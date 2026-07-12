"""Provider abstraction: paid mode (OpenAI) vs free mode.

JARVIS_PROVIDER=paid (default): GPT-4o + DALL-E 3 + OpenAI TTS.
JARVIS_PROVIDER=free: Gemini (free tier, via its OpenAI-compatible endpoint,
so chat + function calling code works unchanged), Pollinations.ai for images
(no key needed) and edge-tts for narration (free Microsoft voices).
"""

import asyncio
import os
import urllib.parse

from openai import OpenAI

PROVIDER = os.environ.get("JARVIS_PROVIDER", "paid").lower()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

CHAT_MODEL = os.environ.get(
    "JARVIS_CHAT_MODEL",
    "gpt-4o" if PROVIDER == "paid" else "gemini-2.5-flash",
)

# Free narration voice — British male, very Jarvis-appropriate.
EDGE_VOICE = os.environ.get("JARVIS_EDGE_VOICE", "en-GB-RyanNeural")

_client = None


def client() -> OpenAI:
    """Chat-completions client. In free mode this is Gemini speaking the
    OpenAI protocol, so tools/function calling work the same way."""
    global _client
    if _client is None:
        if PROVIDER == "free":
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "GEMINI_API_KEY is not configured, sir. Free mode uses "
                    "Google Gemini — create a key at aistudio.google.com/apikey."
                )
            _client = OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL)
        else:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not configured, sir.")
            _client = OpenAI(api_key=api_key)
    return _client


def generate_image(prompt: str, size: str = "1024x1024") -> str:
    """Returns an image URL for the prompt."""
    if PROVIDER == "free":
        width, height = size.split("x")
        return (
            "https://image.pollinations.ai/prompt/"
            + urllib.parse.quote(prompt[:1500])
            + f"?width={width}&height={height}&nologo=true"
        )
    response = client().images.generate(model="dall-e-3", prompt=prompt, n=1, size=size)
    return response.data[0].url


def narrate(text: str, dest: str):
    """Writes spoken narration of `text` to `dest` (mp3)."""
    if PROVIDER == "free":
        import edge_tts

        asyncio.run(edge_tts.Communicate(text, EDGE_VOICE).save(dest))
        return
    with client().audio.speech.with_streaming_response.create(
        model="tts-1", voice="onyx", input=text
    ) as response:
        response.stream_to_file(dest)
