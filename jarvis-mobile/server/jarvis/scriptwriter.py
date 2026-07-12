"""Script generation: GPT produces the topic, spoken narration, scene image
prompts and YouTube metadata for one short video, in a chosen style."""

import json
import random

from . import providers

STYLES = {
    "tech_news": "an energetic tech-news brief about a current technology trend",
    "curiosities": "a mind-blowing curiosities/facts video about an unusual topic",
    "motivation": "a powerful, cinematic motivational speech",
    "science": "a clear, fascinating science explainer for a general audience",
    "top5": "a fast-paced 'Top 5' countdown list on an interesting theme",
    "mystery": "an atmospheric short mystery/unexplained-phenomena story",
}


def pick_auto_style() -> str:
    return random.choice(list(STYLES.keys()))


def write_script(style: str, recent_topics: list[str] | None = None) -> dict:
    """Returns: {topic, narration, scenes: [prompt...], title, description, tags}"""
    if style not in STYLES:
        style = pick_auto_style()
    avoid = ""
    if recent_topics:
        avoid = "Avoid these recently used topics: " + "; ".join(recent_topics[:10]) + ". "

    prompt = (
        f"Write {STYLES[style]} as a vertical YouTube Short (60-90 seconds of narration). "
        f"{avoid}"
        "Return ONLY a JSON object with these keys:\n"
        '  "topic": short topic name,\n'
        '  "narration": the full spoken script, natural spoken English, no stage directions,\n'
        '  "scenes": an array of 5 or 6 vivid image-generation prompts (cinematic, vertical '
        "composition, no text in image) matching the narration in order,\n"
        '  "title": a catchy YouTube title under 90 characters,\n'
        '  "description": 2-3 sentence YouTube description with 3 hashtags,\n'
        '  "tags": array of 8-12 YouTube tags.'
    )

    response = providers.client().chat.completions.create(
        model=providers.CHAT_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a professional YouTube scriptwriter. Output valid JSON only."},
            {"role": "user", "content": prompt},
        ],
    )
    script = _parse_json(response.choices[0].message.content)
    script["style"] = style
    return script


def _parse_json(text: str) -> dict:
    """Tolerates markdown code fences some models wrap around JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)
