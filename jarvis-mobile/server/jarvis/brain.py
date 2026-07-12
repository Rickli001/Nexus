"""J.A.R.V.I.S. persona: conversational brain (GPT) and image generation
(DALL-E) — feature parity with the desktop Nexus app, in Jarvis's voice."""

import os
from openai import OpenAI

_client = None

PERSONA = (
    "You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), a highly "
    "capable AI assistant. You always answer in English with the composed, "
    "polite, dry-witted tone of a British butler. Address the user as 'sir'. "
    "Be concise — your replies are spoken aloud on a phone, so keep them under "
    "three sentences unless the user asks for detail. You also run the user's "
    "YouTube content engine: you write scripts, produce AI-generated videos "
    "and post one every two hours in AUTO mode, or on demand in MANUAL mode. "
    "When asked about the channel or the pipeline, answer from the status "
    "context provided to you."
)


def client():
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured, sir.")
        _client = OpenAI(api_key=api_key)
    return _client


def chat(message: str, status_context: str = "") -> str:
    messages = [{"role": "system", "content": PERSONA}]
    if status_context:
        messages.append({
            "role": "system",
            "content": f"Current content-engine status: {status_context}",
        })
    messages.append({"role": "user", "content": message})
    response = client().chat.completions.create(model="gpt-4o", messages=messages)
    return response.choices[0].message.content


def generate_image(prompt: str, size: str = "1024x1024") -> str:
    response = client().images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size=size,
    )
    return response.data[0].url
