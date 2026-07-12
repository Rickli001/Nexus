"""Persistent memory: rolling conversation history + long-term facts the user
asked Jarvis to remember. Survives restarts (JSON file)."""

import json
import os
import threading

MEMORY_FILE = os.environ.get(
    "JARVIS_MEMORY_FILE",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory.json"),
)

_DEFAULT = {"facts": [], "history": []}
_lock = threading.Lock()

HISTORY_LIMIT = 24  # messages kept in rolling context
FACTS_LIMIT = 100


def _read():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return {**_DEFAULT, **json.load(f)}
        except (json.JSONDecodeError, OSError):
            pass
    return json.loads(json.dumps(_DEFAULT))


def _write(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_facts() -> list[str]:
    with _lock:
        return _read()["facts"]


def remember(fact: str):
    with _lock:
        data = _read()
        if fact not in data["facts"]:
            data["facts"] = (data["facts"] + [fact])[-FACTS_LIMIT:]
            _write(data)


def get_history() -> list[dict]:
    with _lock:
        return _read()["history"]


def append_turn(role: str, content: str):
    with _lock:
        data = _read()
        data["history"] = (data["history"] + [{"role": role, "content": content}])[-HISTORY_LIMIT:]
        _write(data)
