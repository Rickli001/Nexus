"""Fan-out notifications to every configured channel: the PWA's native Web
Push (always available once the user enables it) and the optional Telegram
companion. Both are no-ops when unconfigured; neither ever raises."""

from . import push, telegram_bot


def notify(text: str):
    telegram_bot.notify(text)
    push.notify("J.A.R.V.I.S.", text)


def notify_video(path: str, caption: str):
    telegram_bot.notify_video(path, caption)
    # Web Push can't carry a video file — the app's review player has it.
    push.notify("J.A.R.V.I.S. — awaiting your approval", caption)
