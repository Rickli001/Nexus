"""Optional Telegram companion for J.A.R.V.I.S. — a second remote control.

Completely optional: without TELEGRAM_BOT_TOKEN this module is inert and the
app behaves exactly as before. With it, Jarvis:

- notifies you when a video is posted, fails, or awaits review (sending the
  actual video file so you can watch it in the chat), and
- answers any text message with the same brain as the app ("switch to manual",
  "make a science video", "briefing", "approve the video"...).

Setup (2 minutes):
1. In Telegram, talk to @BotFather -> /newbot -> copy the token.
2. Set TELEGRAM_BOT_TOKEN and start the server.
3. Message your bot once; it replies with your chat id. Set TELEGRAM_CHAT_ID
   to that number and restart. Only that chat is ever obeyed.
"""

import logging
import os
import threading
import time

import requests

log = logging.getLogger("jarvis.telegram")

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
API = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else None


def enabled() -> bool:
    return bool(API)


def _authorized(chat_id) -> bool:
    return bool(CHAT_ID) and str(chat_id) == str(CHAT_ID)


def _send(chat_id, text: str):
    requests.post(
        f"{API}/sendMessage",
        json={"chat_id": chat_id, "text": text[:4000]},
        timeout=30,
    )


def notify(text: str):
    """Push a message to the owner. Silently a no-op if not configured."""
    if not (API and CHAT_ID):
        return
    try:
        _send(CHAT_ID, text)
    except Exception as e:
        log.warning("Telegram notify failed: %s", e)


def notify_video(path: str, caption: str):
    """Send a video file to the owner (e.g. one awaiting review)."""
    if not (API and CHAT_ID):
        return
    try:
        with open(path, "rb") as f:
            requests.post(
                f"{API}/sendVideo",
                data={"chat_id": CHAT_ID, "caption": caption[:1000]},
                files={"video": f},
                timeout=300,
            )
    except Exception as e:
        log.warning("Telegram video failed: %s", e)


def _handle(message: dict):
    chat_id = message.get("chat", {}).get("id")
    text = (message.get("text") or "").strip()
    if not chat_id or not text:
        return
    if not _authorized(chat_id):
        # Help the owner find their id during setup; obey no one else.
        _send(
            chat_id,
            f"This chat id is {chat_id}. If you are my owner, set "
            "TELEGRAM_CHAT_ID to that number and restart me, sir.",
        )
        return
    from . import brain  # lazy: avoids import cycles at module load

    try:
        reply = brain.chat(text)
    except Exception as e:
        reply = f"I ran into trouble, sir: {e}"
    try:
        _send(chat_id, reply)
    except Exception as e:
        log.warning("Telegram reply failed: %s", e)


def _poll_loop():
    offset = None
    while True:
        try:
            response = requests.get(
                f"{API}/getUpdates",
                params={"timeout": 50, "offset": offset},
                timeout=80,
            ).json()
            for update in response.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update:
                    _handle(update["message"])
        except Exception as e:
            log.warning("Telegram polling error (%s); retrying in 10s", e)
            time.sleep(10)


def start():
    if not enabled():
        log.info("Telegram companion disabled (no TELEGRAM_BOT_TOKEN).")
        return
    threading.Thread(target=_poll_loop, daemon=True, name="telegram-bot").start()
    if not CHAT_ID:
        log.warning(
            "Telegram bot online but TELEGRAM_CHAT_ID is unset — message the "
            "bot once to discover your chat id."
        )
    else:
        log.info("Telegram companion online.")
        notify("J.A.R.V.I.S. online and at your service, sir.")
