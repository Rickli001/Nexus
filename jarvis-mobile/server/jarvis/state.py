"""Persistent app state: mode (auto/manual), chosen style, pipeline status,
posting history. Stored as a small JSON file so it survives restarts."""

import json
import os
import threading

STATE_FILE = os.environ.get(
    "JARVIS_STATE_FILE",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state.json"),
)

_DEFAULT = {
    "mode": "auto",            # "auto" | "manual"
    "style": "tech_news",      # style used in manual mode
    "pipeline_stage": "idle",  # idle | writing_script | generating_scenes | narrating | rendering | uploading | error
    "pipeline_detail": "",
    "last_video": None,        # {"title", "video_id", "url", "style", "posted_at"}
    "review_mode": False,      # when True, videos wait for approval before upload
    "pending_video": None,     # {"path", "title", "description", "tags", "style", "topic", "created_at"}
    "history": [],
}

_lock = threading.Lock()


def _read():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**_DEFAULT, **data}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_DEFAULT)


def get_state():
    with _lock:
        return _read()


def update_state(**changes):
    with _lock:
        data = _read()
        data.update(changes)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data


def append_history(entry, keep=50):
    with _lock:
        data = _read()
        data["history"] = ([entry] + data.get("history", []))[:keep]
        data["last_video"] = entry
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data
