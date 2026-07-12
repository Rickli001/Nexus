"""Video pipeline: script -> DALL-E scene images -> OpenAI TTS narration ->
moviepy assembly (1080x1920 vertical) -> YouTube upload."""

import datetime
import os
import tempfile

import requests

from . import brain, scriptwriter, state, youtube

# moviepy 2.x renamed the import path and the clip mutators
try:  # moviepy >= 2.0
    from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
except ImportError:  # moviepy 1.x
    from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips


def _with_duration(clip, seconds):
    return clip.with_duration(seconds) if hasattr(clip, "with_duration") else clip.set_duration(seconds)


def _with_audio(clip, audio):
    return clip.with_audio(audio) if hasattr(clip, "with_audio") else clip.set_audio(audio)


def _stage(stage, detail=""):
    state.update_state(pipeline_stage=stage, pipeline_detail=detail)


def _download(url: str, dest: str):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with open(dest, "wb") as f:
        f.write(r.content)


def _narrate(text: str, dest: str):
    # "onyx" is the deepest English voice available — calm and composed.
    with brain.client().audio.speech.with_streaming_response.create(
        model="tts-1", voice="onyx", input=text
    ) as response:
        response.stream_to_file(dest)


def run_pipeline(style: str) -> dict:
    """Produce and upload one video. Returns the history entry. Raises on failure."""
    try:
        recent = [h.get("topic", "") for h in state.get_state().get("history", [])]

        _stage("writing_script", f"style={style}")
        script = scriptwriter.write_script(style, recent_topics=recent)

        with tempfile.TemporaryDirectory(prefix="jarvis_video_") as workdir:
            _stage("generating_scenes", script.get("topic", ""))
            image_paths = []
            for i, scene_prompt in enumerate(script["scenes"]):
                url = brain.generate_image(
                    f"Cinematic vertical composition, high detail, no text: {scene_prompt}",
                    size="1024x1792",
                )
                path = os.path.join(workdir, f"scene_{i}.png")
                _download(url, path)
                image_paths.append(path)

            _stage("narrating")
            audio_path = os.path.join(workdir, "narration.mp3")
            _narrate(script["narration"], audio_path)

            _stage("rendering")
            audio = AudioFileClip(audio_path)
            per_scene = audio.duration / len(image_paths)
            clips = [_with_duration(ImageClip(p), per_scene) for p in image_paths]
            video = _with_audio(concatenate_videoclips(clips, method="compose"), audio)
            video_path = os.path.join(workdir, "final.mp4")
            video.write_videofile(
                video_path, fps=24, codec="libx264", audio_codec="aac", logger=None
            )

            _stage("uploading", script.get("title", ""))
            video_id = youtube.upload_video(
                video_path,
                title=script["title"],
                description=script["description"],
                tags=script.get("tags", []),
            )

        entry = {
            "title": script["title"],
            "topic": script.get("topic", ""),
            "style": script["style"],
            "video_id": video_id,
            "url": f"https://youtu.be/{video_id}",
            "posted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        state.append_history(entry)
        _stage("idle")
        return entry
    except Exception as e:
        _stage("error", str(e)[:300])
        raise
