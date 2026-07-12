"""Native Web Push notifications for the PWA — no third-party app involved.

VAPID keys are generated automatically on first boot (vapid_private.pem).
The app subscribes via /push/subscribe; subscriptions are stored in a JSON
file and pruned when the browser reports them gone (404/410).

Requires the app to be served over HTTPS (or localhost) — a Web Platform
rule, not ours."""

import base64
import json
import logging
import os
import threading

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid02
from pywebpush import WebPushException, webpush

log = logging.getLogger("jarvis.push")

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAPID_FILE = os.environ.get("JARVIS_VAPID_FILE", os.path.join(_BASE_DIR, "vapid_private.pem"))
SUBS_FILE = os.environ.get("JARVIS_PUSH_SUBS_FILE", os.path.join(_BASE_DIR, "push_subs.json"))
CLAIM_SUB = os.environ.get("JARVIS_PUSH_EMAIL", "mailto:jarvis@localhost.local")

_lock = threading.Lock()
_vapid = None


def _get_vapid() -> Vapid02:
    global _vapid
    if _vapid is None:
        if not os.path.exists(VAPID_FILE):
            v = Vapid02()
            v.generate_keys()
            v.save_key(VAPID_FILE)
            log.info("Generated new VAPID key pair at %s", VAPID_FILE)
        _vapid = Vapid02.from_file(VAPID_FILE)
    return _vapid


def public_key() -> str:
    """applicationServerKey the browser needs to subscribe (base64url)."""
    raw = _get_vapid().public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _read_subs() -> list[dict]:
    if os.path.exists(SUBS_FILE):
        try:
            with open(SUBS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _write_subs(subs: list[dict]):
    with open(SUBS_FILE, "w", encoding="utf-8") as f:
        json.dump(subs, f, indent=2)


def subscribe(subscription: dict):
    with _lock:
        subs = _read_subs()
        if not any(s.get("endpoint") == subscription.get("endpoint") for s in subs):
            subs.append(subscription)
            _write_subs(subs)
    log.info("Push subscription registered (%d device(s)).", len(_read_subs()))


def unsubscribe(endpoint: str):
    with _lock:
        subs = [s for s in _read_subs() if s.get("endpoint") != endpoint]
        _write_subs(subs)


def device_count() -> int:
    return len(_read_subs())


def notify(title: str, body: str):
    """Push to every registered device. Never raises."""
    subs = _read_subs()
    if not subs:
        return
    _get_vapid()  # ensure the key exists
    dead = []
    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps({"title": title, "body": body[:500]}),
                vapid_private_key=VAPID_FILE,
                vapid_claims={"sub": CLAIM_SUB},
            )
        except WebPushException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):  # browser dropped the subscription
                dead.append(sub.get("endpoint"))
            else:
                log.warning("Push delivery failed: %s", e)
        except Exception as e:
            log.warning("Push delivery failed: %s", e)
    if dead:
        with _lock:
            _write_subs([s for s in _read_subs() if s.get("endpoint") not in dead])
