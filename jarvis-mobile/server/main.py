"""J.A.R.V.I.S. Mobile — backend API.

Run:  uvicorn main:app --host 0.0.0.0 --port 8741
"""

import base64
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from jarvis import (
    audience,
    brain,
    briefing,
    coder,
    providers,
    push,
    scheduler,
    scriptwriter,
    state,
    telegram_bot,
    video_factory,
    youtube,
)

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler.start()
    telegram_bot.start()  # inert unless TELEGRAM_BOT_TOKEN is set
    yield


app = FastAPI(title="J.A.R.V.I.S. Mobile API", lifespan=lifespan)

# --- Access control ---
# Set JARVIS_API_KEY to lock the API down; every request must then carry it
# in the X-Jarvis-Key header (or ?key= for media URLs). Unset = open, for
# local development only.
API_KEY = os.environ.get("JARVIS_API_KEY")
_PUBLIC_PREFIXES = ("/app",)  # the PWA shell itself is public; the API is not


@app.middleware("http")
async def require_api_key(request, call_next):
    if (
        API_KEY
        and request.method != "OPTIONS"
        and not request.url.path.startswith(_PUBLIC_PREFIXES)
    ):
        supplied = request.headers.get("x-jarvis-key") or request.query_params.get("key")
        if supplied != API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


# Added after the auth middleware so CORS headers are present on 401s too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the PWA from the same container at /app/ (single-box deploy).
_APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if os.path.isdir(_APP_DIR):
    app.mount("/app", StaticFiles(directory=_APP_DIR, html=True), name="app")


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


class PushSubscribeIn(BaseModel):
    subscription: dict


class PushUnsubscribeIn(BaseModel):
    endpoint: str


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
        return {"reply": coder.code(body.prompt), "model": coder.active_model()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/briefing")
def get_briefing():
    try:
        return {"briefing": briefing.compose()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/comments")
def comments():
    try:
        return {"analysis": audience.analyze()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/image")
def image(body: ImageIn):
    try:
        return {"url": brain.generate_image(body.prompt)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/image/edit")
async def image_edit(file: UploadFile = File(...), prompt: str = Form(...)):
    try:
        data = await file.read()
        out, mime = providers.edit_image(data, file.content_type or "image/png", prompt)
        return {"image": f"data:{mime};base64,{base64.b64encode(out).decode()}"}
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


@app.get("/push/key")
def push_key():
    return {"key": push.public_key()}


@app.post("/push/subscribe")
def push_subscribe(body: PushSubscribeIn):
    if not body.subscription.get("endpoint"):
        raise HTTPException(status_code=422, detail="invalid subscription")
    push.subscribe(body.subscription)
    return {"ok": True, "devices": push.device_count()}


@app.post("/push/unsubscribe")
def push_unsubscribe(body: PushUnsubscribeIn):
    push.unsubscribe(body.endpoint)
    return {"ok": True, "devices": push.device_count()}


@app.post("/push/test")
def push_test():
    push.notify("J.A.R.V.I.S.", "Push notifications are operational, sir.")
    return {"sent_to": push.device_count()}


@app.get("/channel")
def channel():
    try:
        return youtube.channel_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
