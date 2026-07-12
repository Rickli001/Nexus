"""Video pipeline: script -> DALL-E scene images -> OpenAI TTS narration ->
moviepy assembly (1080x1920 vertical) -> YouTube upload.

With review mode on, the rendered video is held in PENDING_DIR and only
uploaded after the user approves it in the app (or by voice)."""

import datetime
import os
import shutil
import tempfile

import requests

from . import brain, providers, scriptwriter, state, youtube

# moviepy 2.x renamed the import path and the clip mutators
try:  # moviepy >= 2.0
    from moviepy import AudioFileClip, CompositeAudioClip, ImageClip, concatenate_videoclips
except ImportError:  # moviepy 1.x
    from moviepy.editor import AudioFileClip, CompositeAudioClip, ImageClip, concatenate_videoclips


def _with_duration(clip, seconds):
    return clip.with_duration(seconds) if hasattr(clip, "with_duration") else clip.set_duration(seconds)


def _with_audio(clip, audio):
    return clip.with_audio(audio) if hasattr(clip, "with_audio") else clip.set_audio(audio)


def _subclip(clip, start, end):
    return clip.subclipped(start, end) if hasattr(clip, "subclipped") else clip.subclip(start, end)


def _with_volume(clip, factor):
    return (
        clip.with_volume_scaled(factor)
        if hasattr(clip, "with_volume_scaled")
        else clip.volumex(factor)
    )


PENDING_DIR = os.environ.get(
    "JARVIS_PENDING_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pending"),
)

# Drop royalty-free .mp3 files here (e.g. from the YouTube Audio Library)
# and every video gets a soft background track mixed under the narration.
MUSIC_DIR = os.environ.get(
    "JARVIS_MUSIC_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "music"),
)
MUSIC_VOLUME = float(os.environ.get("JARVIS_MUSIC_VOLUME", "0.12"))


def _stage(stage, detail=""):
    state.update_state(pipeline_stage=stage, pipeline_detail=detail)


def _download(url: str, dest: str):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with open(dest, "wb") as f:
        f.write(r.content)


def _narrate(text: str, dest: str):
    # Paid: OpenAI "onyx" (deep, composed). Free: edge-tts British male.
    providers.narrate(text, dest)


def _soundtrack(narration):
    """Mix a random background track (if any) softly under the narration."""
    import random

    if not os.path.isdir(MUSIC_DIR):
        return narration
    tracks = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith((".mp3", ".wav", ".m4a"))]
    if not tracks:
        return narration
    music = AudioFileClip(os.path.join(MUSIC_DIR, random.choice(tracks)))
    music = _subclip(music, 0, min(music.duration, narration.duration))
    music = _with_volume(music, MUSIC_VOLUME)
    return CompositeAudioClip([narration, music])


def _apply_thumbnail(video_id: str, thumbnail_prompt: str):
    """Generate and set a custom thumbnail. Non-fatal on failure (e.g. the
    channel isn't phone-verified yet)."""
    if not thumbnail_prompt:
        return
    try:
        size = "1792x1024" if providers.PROVIDER == "paid" else "1280x720"
        url = providers.generate_image(
            f"YouTube thumbnail, bold, high contrast, cinematic lighting, no text: {thumbnail_prompt}",
            size=size,
        )
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            _download(url, tmp.name)
            youtube.set_thumbnail(video_id, tmp.name)
        os.unlink(tmp.name)
    except Exception as e:
        import logging

        logging.getLogger("jarvis.video").warning("Thumbnail skipped: %s", e)


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
            narration = AudioFileClip(audio_path)
            audio = _soundtrack(narration)
            per_scene = narration.duration / len(image_paths)
            clips = [_with_duration(ImageClip(p), per_scene) for p in image_paths]
            video = _with_audio(concatenate_videoclips(clips, method="compose"), audio)
            video_path = os.path.join(workdir, "final.mp4")
            video.write_videofile(
                video_path, fps=24, codec="libx264", audio_codec="aac", logger=None
            )

            if state.get_state().get("review_mode"):
                # Hold for approval instead of uploading.
                os.makedirs(PENDING_DIR, exist_ok=True)
                pending_path = os.path.join(PENDING_DIR, "pending.mp4")
                shutil.move(video_path, pending_path)
                pending = {
                    "path": pending_path,
                    "title": script["title"],
                    "description": script["description"],
                    "tags": script.get("tags", []),
                    "style": script["style"],
                    "topic": script.get("topic", ""),
                    "thumbnail_prompt": script.get("thumbnail_prompt", ""),
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
                state.update_state(pending_video=pending)
                _stage("awaiting_review", script["title"])
                return pending

            _stage("uploading", script.get("title", ""))
            video_id = youtube.upload_video(
                video_path,
                title=script["title"],
                description=script["description"],
                tags=script.get("tags", []),
            )
            _apply_thumbnail(video_id, script.get("thumbnail_prompt", ""))

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


def approve_pending() -> dict:
    """Upload the video that is awaiting review."""
    pending = state.get_state().get("pending_video")
    if not pending or not os.path.exists(pending["path"]):
        raise RuntimeError("There is no video awaiting review, sir.")
    _stage("uploading", pending["title"])
    try:
        video_id = youtube.upload_video(
            pending["path"],
            title=pending["title"],
            description=pending["description"],
            tags=pending.get("tags", []),
        )
    except Exception as e:
        _stage("awaiting_review", pending["title"])  # keep it reviewable
        raise RuntimeError(f"Upload failed: {e}")
    _apply_thumbnail(video_id, pending.get("thumbnail_prompt", ""))
    os.remove(pending["path"])
    entry = {
        "title": pending["title"],
        "topic": pending.get("topic", ""),
        "style": pending.get("style", ""),
        "video_id": video_id,
        "url": f"https://youtu.be/{video_id}",
        "posted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    state.update_state(pending_video=None)
    state.append_history(entry)
    _stage("idle")
    return entry


def discard_pending():
    """Delete the video that is awaiting review without posting it."""
    pending = state.get_state().get("pending_video")
    if not pending:
        raise RuntimeError("There is no video awaiting review, sir.")
    if os.path.exists(pending["path"]):
        os.remove(pending["path"])
    state.update_state(pending_video=None)
    _stage("idle")
