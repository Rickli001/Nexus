"""Posting scheduler: one pipeline run every POST_INTERVAL_HOURS (default 2).
The scheduled job only produces a video in AUTO mode; MANUAL mode posts only
when triggered from the app. A lock prevents overlapping runs."""

import logging
import os
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from . import optimizer, state, video_factory

log = logging.getLogger("jarvis.scheduler")

INTERVAL_HOURS = float(os.environ.get("POST_INTERVAL_HOURS", "2"))

_scheduler = None
_pipeline_lock = threading.Lock()


def _run_pipeline_locked(style: str):
    if not _pipeline_lock.acquire(blocking=False):
        log.warning("Pipeline already running; skipping this trigger.")
        return
    try:
        video_factory.run_pipeline(style)
    except Exception:
        log.exception("Pipeline run failed")
    finally:
        _pipeline_lock.release()


def _scheduled_job():
    s = state.get_state()
    if s["mode"] != "auto":
        log.info("Manual mode active; scheduled slot skipped.")
        return
    if s.get("pending_video"):
        log.info("A video is awaiting review; scheduled slot skipped.")
        return
    _run_pipeline_locked(optimizer.pick_style())


def start():
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _scheduled_job,
        IntervalTrigger(hours=INTERVAL_HOURS),
        id="auto_post",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    log.info("Scheduler started: one post every %s hour(s) in AUTO mode.", INTERVAL_HOURS)
    return _scheduler


def next_post_at():
    if _scheduler is None:
        return None
    job = _scheduler.get_job("auto_post")
    if job and job.next_run_time and state.get_state()["mode"] == "auto":
        return job.next_run_time.isoformat()
    return None


def trigger_manual(style: str) -> bool:
    """Fire one pipeline run now, in a background thread. Returns False if busy."""
    if _pipeline_lock.locked():
        return False
    threading.Thread(target=_run_pipeline_locked, args=(style,), daemon=True).start()
    return True


def is_busy() -> bool:
    return _pipeline_lock.locked()
