"""Provider abstraction: paid mode (OpenAI) vs free mode.

JARVIS_PROVIDER=paid (default): GPT-4o + DALL-E 3 + OpenAI TTS.
JARVIS_PROVIDER=free: Gemini (free tier, via its OpenAI-compatible endpoint,
so chat + function calling code works unchanged), Pollinations.ai for images
(no key needed) and edge-tts for narration (free Microsoft voices).
"""

import asyncio
import base64
import os
import urllib.parse

import requests
from openai import OpenAI

PROVIDER = os.environ.get("JARVIS_PROVIDER", "paid").lower()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

CHAT_MODEL = os.environ.get(
    "JARVIS_CHAT_MODEL",
    "gpt-4o" if PROVIDER == "paid" else "gemini-2.5-flash",
)

# Free narration voice — British male, very Jarvis-appropriate.
EDGE_VOICE = os.environ.get("JARVIS_EDGE_VOICE", "en-GB-RyanNeural")

# Image editing model in free mode (Gemini's image model, aka "nano banana").
IMAGE_EDIT_MODEL = os.environ.get("JARVIS_IMAGE_MODEL", "gemini-2.5-flash-image")

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


def edit_image(image_bytes: bytes, mime: str, prompt: str) -> tuple[bytes, str]:
    """Edit an existing image per the instruction. Returns (bytes, mime)."""
    if PROVIDER == "free":
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured, sir. Free mode uses "
                "Google Gemini — create a key at aistudio.google.com/apikey."
            )
        body = {
            "contents": [{
                "parts": [
                    {"inlineData": {"mimeType": mime, "data": base64.b64encode(image_bytes).decode()}},
                    {"text": prompt},
                ]
            }]
        }
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{IMAGE_EDIT_MODEL}:generateContent",
            headers={"x-goog-api-key": api_key},
            json=body,
            timeout=180,
        )
        response.raise_for_status()
        candidates = response.json().get("candidates", [])
        for part in (candidates[0].get("content", {}).get("parts", []) if candidates else []):
            blob = part.get("inlineData") or part.get("inline_data")
            if blob and blob.get("data"):
                return base64.b64decode(blob["data"]), blob.get("mimeType", "image/png")
        raise RuntimeError("The model returned no image, sir.")

    result = client().images.edit(
        model="gpt-image-1",
        image=("image.png", image_bytes, mime),
        prompt=prompt,
    )
    return base64.b64decode(result.data[0].b64_json), "image/png"


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
