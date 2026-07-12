"""J.A.R.V.I.S. Mobile — backend API.

Run:  uvicorn main:app --host 0.0.0.0 --port 8741
"""

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from jarvis import brain, scheduler, scriptwriter, state, youtube

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler.start()
    yield


app = FastAPI(title="J.A.R.V.I.S. Mobile API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatIn(BaseModel):
    message: str


class ImageIn(BaseModel):
    prompt: str


class ModeIn(BaseModel):
    mode: str
    style: str | None = None


class GenerateIn(BaseModel):
    style: str


def _status_payload():
    s = state.get_state()
    return {
        "mode": s["mode"],
        "style": s["style"],
        "pipeline_stage": s["pipeline_stage"],
        "pipeline_detail": s["pipeline_detail"],
        "busy": scheduler.is_busy(),
        "next_post_at": scheduler.next_post_at(),
        "last_video": s["last_video"],
        "styles": list(scriptwriter.STYLES.keys()),
    }


@app.get("/status")
def get_status():
    return _status_payload()


@app.post("/chat")
def chat(body: ChatIn):
    try:
        context = json.dumps(_status_payload(), default=str)
        return {"reply": brain.chat(body.message, status_context=context)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/image")
def image(body: ImageIn):
    try:
        return {"url": brain.generate_image(body.prompt)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mode")
def set_mode(body: ModeIn):
    if body.mode not in ("auto", "manual"):
        raise HTTPException(status_code=422, detail="mode must be 'auto' or 'manual'")
    changes = {"mode": body.mode}
    if body.style:
        if body.style not in scriptwriter.STYLES:
            raise HTTPException(status_code=422, detail="unknown style")
        changes["style"] = body.style
    state.update_state(**changes)
    return _status_payload()


@app.post("/generate")
def generate(body: GenerateIn):
    if body.style not in scriptwriter.STYLES:
        raise HTTPException(status_code=422, detail="unknown style")
    state.update_state(style=body.style)
    if not scheduler.trigger_manual(body.style):
        return {"started": False, "detail": "A video is already in production, sir."}
    return {"started": True, "detail": "Production has begun, sir. I shall post it shortly."}


@app.get("/channel")
def channel():
    try:
        return youtube.channel_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
