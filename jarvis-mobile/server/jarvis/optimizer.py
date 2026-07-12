"""Style optimizer for AUTO mode: instead of picking a random style, favor
the styles whose posted videos earn the most views on this channel.

Epsilon-greedy: most of the time pick the best-performing style, but keep
exploring other styles ~30% of the time so new winners can emerge."""

import logging
import random
from collections import defaultdict

from . import scriptwriter, state, youtube

log = logging.getLogger("jarvis.optimizer")

EXPLORE_RATE = 0.3
MIN_STYLES_WITH_DATA = 2


def pick_style() -> str:
    if random.random() < EXPLORE_RATE:
        style = scriptwriter.pick_auto_style()
        log.info("Style pick (exploring): %s", style)
        return style

    history = state.get_state().get("history", [])[:20]
    by_id = {h["video_id"]: h.get("style") for h in history if h.get("video_id") and h.get("style")}
    if not by_id:
        return scriptwriter.pick_auto_style()

    try:
        stats = youtube.videos_stats(list(by_id.keys()))
    except Exception as e:
        log.warning("Could not fetch video stats (%s); picking randomly.", e)
        return scriptwriter.pick_auto_style()

    views_by_style = defaultdict(list)
    for s in stats:
        style = by_id.get(s["video_id"])
        if style:
            views_by_style[style].append(int(s.get("views") or 0))

    if len(views_by_style) < MIN_STYLES_WITH_DATA:
        return scriptwriter.pick_auto_style()

    averages = {style: sum(v) / len(v) for style, v in views_by_style.items()}
    best = max(averages, key=averages.get)
    log.info("Style pick (optimized): %s — avg views %s", best, {k: round(v) for k, v in averages.items()})
    return best
