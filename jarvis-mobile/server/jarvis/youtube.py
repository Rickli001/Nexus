"""YouTube integration: authenticated upload (videos.insert) and channel
statistics (channels.list) via the YouTube Data API v3.

Auth: run authorize_youtube.py once to create token.json from your OAuth
client_secret.json (see README)."""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.environ.get("YT_TOKEN_FILE", os.path.join(_BASE_DIR, "token.json"))
PRIVACY = os.environ.get("YT_PRIVACY", "private")  # private | unlisted | public

AI_DISCLOSURE = (
    "\n\n---\nThis video was generated with AI (script, visuals and narration) "
    "and posted automatically by J.A.R.V.I.S."
)

_service = None


def get_service():
    global _service
    if _service is None:
        if not os.path.exists(TOKEN_FILE):
            raise RuntimeError(
                "YouTube is not authorized yet. Run authorize_youtube.py first (see README)."
            )
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
        _service = build("youtube", "v3", credentials=creds)
    return _service


def upload_video(path: str, title: str, description: str, tags: list[str]) -> str:
    """Uploads the file and returns the YouTube video id."""
    body = {
        "snippet": {
            "title": title[:100],
            "description": (description + AI_DISCLOSURE)[:4900],
            "tags": tags[:15],
            "categoryId": "24",  # Entertainment
        },
        "status": {
            "privacyStatus": PRIVACY,
            "selfDeclaredMadeForKids": False,
            # Required disclosure for realistic AI-generated/altered content
            "containsSyntheticMedia": True,
        },
    }
    media = MediaFileUpload(path, mimetype="video/mp4", resumable=True)
    request = get_service().videos().insert(
        part="snippet,status", body=body, media_body=media
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]


def videos_stats(video_ids: list[str]) -> list[dict]:
    """Views/likes/comments for a batch of videos (for the daily briefing)."""
    response = (
        get_service()
        .videos()
        .list(part="snippet,statistics", id=",".join(video_ids[:50]))
        .execute()
    )
    out = []
    for v in response.get("items", []):
        stats = v.get("statistics", {})
        out.append({
            "title": v["snippet"]["title"],
            "video_id": v["id"],
            "views": stats.get("viewCount"),
            "likes": stats.get("likeCount"),
            "comments": stats.get("commentCount"),
        })
    return out


def channel_stats() -> dict:
    response = get_service().channels().list(part="snippet,statistics", mine=True).execute()
    items = response.get("items", [])
    if not items:
        return {"error": "No channel found for this account."}
    ch = items[0]
    stats = ch["statistics"]
    return {
        "channel": ch["snippet"]["title"],
        "subscribers": stats.get("subscriberCount"),
        "views": stats.get("viewCount"),
        "videos": stats.get("videoCount"),
    }
