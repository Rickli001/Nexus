"""Audience analysis: Jarvis reads the channel's recent comments, summarizes
sentiment and highlights, and suggests topics the audience is asking for."""

import json

from . import providers, state, youtube


def analyze() -> str:
    comments = youtube.recent_comments(50)
    if not comments:
        return "There are no comments on the channel yet, sir. Early days."

    # Attach video titles from our posting history where we can.
    titles = {h.get("video_id"): h.get("title") for h in state.get_state().get("history", [])}
    for c in comments:
        c["video"] = titles.get(c.pop("video_id", None))

    response = providers.client().chat.completions.create(
        model=providers.CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are J.A.R.V.I.S. reporting to 'sir' in spoken English, composed "
                    "British butler tone, no markdown (read aloud). Analyze these YouTube "
                    "comments in at most 7 short sentences: overall sentiment, what people "
                    "liked or complained about (quote at most one short comment), which "
                    "video is generating the most conversation, and finish with 2-3 "
                    "concrete video topic suggestions the audience seems to want."
                ),
            },
            {"role": "user", "content": json.dumps(comments, ensure_ascii=False)},
        ],
    )
    return response.choices[0].message.content
