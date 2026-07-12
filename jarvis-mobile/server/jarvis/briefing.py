"""Daily briefing: channel stats + performance of recently posted videos,
composed by GPT into a short spoken report in Jarvis's voice."""

import json

from . import providers, state, youtube


def gather() -> dict:
    data = {"channel": None, "recent_videos": [], "content_engine": {}}
    s = state.get_state()
    data["content_engine"] = {
        "mode": s["mode"],
        "style": s["style"],
        "pipeline_stage": s["pipeline_stage"],
        "last_video": s["last_video"],
        "review_mode": s.get("review_mode", False),
        "pending_video": (s.get("pending_video") or {}).get("title"),
    }
    try:
        data["channel"] = youtube.channel_stats()
        ids = [h["video_id"] for h in s.get("history", [])[:5] if h.get("video_id")]
        if ids:
            data["recent_videos"] = youtube.videos_stats(ids)
    except Exception as e:
        data["channel_error"] = str(e)
    return data


def compose() -> str:
    data = gather()
    response = providers.client().chat.completions.create(
        model=providers.CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are J.A.R.V.I.S. delivering a spoken daily briefing to 'sir' in "
                    "English, in the composed tone of a British butler. Summarize the data "
                    "in at most 6 short sentences: channel growth, how the recent videos "
                    "are performing (views/likes, call out the best one), and the content "
                    "engine status (mode, next steps, anything awaiting review). If data "
                    "is missing or errored, mention it briefly and move on. No markdown — "
                    "this is read aloud."
                ),
            },
            {"role": "user", "content": json.dumps(data, ensure_ascii=False, default=str)},
        ],
    )
    return response.choices[0].message.content
