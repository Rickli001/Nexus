"""J.A.R.V.I.S. Mobile — backend API.

Run:  uvicorn main:app --host 0.0.0.0 --port 8741
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from jarvis import brain, briefing, coder, scheduler, scriptwriter, state, video_factory, youtube

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
    review: bool | None = None


class GenerateIn(BaseModel):
    style: str


class CodeIn(BaseModel):
    prompt: str


class ReviewIn(BaseModel):
    action: str  # "approve" | "discard"


def _status_payload():
    s = state.get_state()
    pending = s.get("pending_video")
    return {
        "mode": s["mode"],
        "style": s["style"],
        "pipeline_stage": s["pipeline_stage"],
        "pipeline_detail": s["pipeline_detail"],
        "busy": scheduler.is_busy(),
        "next_post_at": scheduler.next_post_at(),
        "last_video": s["last_video"],
        "review_mode": s.get("review_mode", False),
        "pending_video": {"title": pending["title"], "style": pending["style"]} if pending else None,
        "styles": list(scriptwriter.STYLES.keys()),
    }


@app.get("/status")
def get_status():
    return _status_payload()


@app.post("/chat")
def chat(body: ChatIn):
    try:
        return {"reply": brain.chat(body.message)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/code")
def code(body: CodeIn):
    try:
        return {"reply": coder.code(body.prompt), "model": coder.MODEL}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/briefing")
def get_briefing():
    try:
        return {"briefing": briefing.compose()}
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
    if body.review is not None:
        changes["review_mode"] = body.review
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


@app.get("/pending/video")
def pending_video():
    pending = state.get_state().get("pending_video")
    if not pending or not os.path.exists(pending["path"]):
        raise HTTPException(status_code=404, detail="No video awaiting review.")
    return FileResponse(pending["path"], media_type="video/mp4", filename="pending.mp4")


@app.post("/review")
def review(body: ReviewIn):
    if body.action not in ("approve", "discard"):
        raise HTTPException(status_code=422, detail="action must be 'approve' or 'discard'")
    try:
        if body.action == "approve":
            entry = video_factory.approve_pending()
            return {"posted": True, "video": entry}
        video_factory.discard_pending()
        return {"posted": False, "discarded": True}
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.get("/channel")
def channel():
    try:
        return youtube.channel_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
