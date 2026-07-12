"""J.A.R.V.I.S. coding mode.

Preferred engine: Claude via the Anthropic SDK (needs ANTHROPIC_API_KEY).
Model defaults to claude-fable-5 (override with CLAUDE_MODEL). On Fable 5,
thinking is always on (no `thinking` parameter is sent) and a server-side
fallback to claude-opus-4-8 is enabled so a safety-classifier decline on a
benign request still gets answered.

In free mode (JARVIS_PROVIDER=free) without an Anthropic key, coding falls
back to the free provider's chat model (Gemini).
"""

import os

import anthropic

from . import memory, providers

MODEL = os.environ.get("CLAUDE_MODEL", "claude-fable-5")
FALLBACK_MODEL = "claude-opus-4-8"

_client = None

SYSTEM = (
    "You are J.A.R.V.I.S. in coding mode: a world-class software engineer with "
    "the composed, dry-witted tone of a British butler (address the user as "
    "'sir', but keep the persona to one line at most — the code is the point). "
    "Produce complete, working, production-quality code with sensible structure "
    "and no placeholder stubs. Explain briefly what the code does and how to "
    "run it. Use Markdown code blocks with the language tag."
)


def client():
    global _client
    if _client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY is not configured, sir.")
        _client = anthropic.Anthropic()
    return _client


def active_model() -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return MODEL
    if providers.PROVIDER == "free":
        return providers.CHAT_MODEL
    return MODEL  # will raise a clear missing-key error in code()


def code(prompt: str) -> str:
    facts = memory.get_facts()
    system = SYSTEM
    if facts:
        system += "\n\nThings you remember about the user:\n- " + "\n- ".join(facts)

    # Free mode without an Anthropic key: use the free chat model instead.
    if not os.environ.get("ANTHROPIC_API_KEY") and providers.PROVIDER == "free":
        response = providers.client().chat.completions.create(
            model=providers.CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    kwargs = dict(
        model=MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if MODEL == "claude-fable-5":
        # Server-side fallback: on a policy decline, Opus 4.8 answers instead.
        response = client().beta.messages.create(
            betas=["server-side-fallback-2026-06-01"],
            fallbacks=[{"model": FALLBACK_MODEL}],
            **kwargs,
        )
    else:
        response = client().messages.create(**kwargs)

    if response.stop_reason == "refusal":
        return "I'm afraid I must decline that particular request, sir."
    return "".join(b.text for b in response.content if b.type == "text")
