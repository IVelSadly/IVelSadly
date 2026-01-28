from __future__ import annotations

import hmac
import logging
import time
import uuid
from hashlib import sha256
from typing import Any, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, ValidationError
from pydantic.config import ConfigDict

from .config import settings
from .whatsapp import WhatsAppAPIError, send_text_message

app = FastAPI(title="WhatsApp Bot MVP - Passo 1")

logger = logging.getLogger("whatsapp-bot")
logging.basicConfig(level=logging.INFO)

SIGNATURE_HEADER = "x-hub-signature-256"
MESSAGE_CACHE_TTL_SECONDS = 600
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_EVENTS = 20

message_cache: dict[str, float] = {}
rate_limit_cache: dict[str, list[float]] = {}


class TextContent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    body: str


class Message(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    from_: str = Field(alias="from")
    id: str
    type: str
    text: Optional[TextContent] = None

    @property
    def sender(self) -> str:
        return self.from_


class Contact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    wa_id: str


class Value(BaseModel):
    model_config = ConfigDict(extra="ignore")

    messages: Optional[list[Message]] = None
    contacts: Optional[list[Contact]] = None


class Change(BaseModel):
    model_config = ConfigDict(extra="ignore")

    value: Value


class Entry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    changes: list[Change]


class WebhookPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entry: list[Entry]


@app.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(
    hub_mode: str | None = None,
    hub_verify_token: str | None = None,
    hub_challenge: str | None = None,
) -> str:
    if not settings.whatsapp_verify_token:
        raise HTTPException(status_code=500, detail="WHATSAPP_VERIFY_TOKEN is not set.")

    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return hub_challenge or ""

    raise HTTPException(status_code=403, detail="Verification failed.")


@app.post("/webhook")
async def receive_webhook(
    request: Request, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    body = await request.body()
    signature = request.headers.get(SIGNATURE_HEADER)

    if not settings.whatsapp_app_secret:
        raise HTTPException(status_code=500, detail="WHATSAPP_APP_SECRET is not set.")

    if not signature or not _is_signature_valid(body, signature, settings.whatsapp_app_secret):
        logger.warning("Invalid webhook signature", extra={"request_id": request_id})
        raise HTTPException(status_code=401, detail="Invalid signature.")

    try:
        payload = WebhookPayload.model_validate_json(body)
    except ValidationError as error:
        logger.warning("Invalid webhook payload", extra={"request_id": request_id})
        raise HTTPException(status_code=400, detail="Invalid payload.") from error

    ip_address = request.client.host if request.client else "unknown"
    if _is_rate_limited(ip_address):
        logger.warning("Rate limit exceeded", extra={"request_id": request_id})
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    if not payload.entry:
        raise HTTPException(status_code=400, detail="Invalid payload.")

    if not payload.entry[0].changes:
        raise HTTPException(status_code=400, detail="Invalid payload.")

    value = payload.entry[0].changes[0].value
    messages = value.messages or []

    if not messages:
        return {"status": "ignored", "reason": "no_messages", "request_id": request_id}

    message = messages[0]
    if message.type != "text" or not message.text or not message.text.body.strip():
        return {"status": "ignored", "reason": "non_text_message", "request_id": request_id}

    if _is_duplicate_message(message.id):
        return {"status": "ignored", "reason": "duplicate_message", "request_id": request_id}

    wa_id = message.sender or (value.contacts[0].wa_id if value.contacts else None)
    if not wa_id:
        return {"status": "ignored", "reason": "missing_wa_id", "request_id": request_id}

    if _is_rate_limited(wa_id):
        logger.warning("Rate limit exceeded for wa_id", extra={"request_id": request_id})
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    response_text = f"Recebido: {message.text.body.strip()}"
    background_tasks.add_task(_send_reply, wa_id, response_text, request_id)

    return {"status": "accepted", "request_id": request_id}


def _is_signature_valid(body: bytes, signature_header: str, app_secret: str) -> bool:
    if not signature_header.startswith("sha256="):
        return False

    received_signature = signature_header.split("=", 1)[1]
    computed_signature = hmac.new(app_secret.encode(), body, sha256).hexdigest()
    return hmac.compare_digest(received_signature, computed_signature)


def _is_duplicate_message(message_id: str) -> bool:
    now = time.time()
    _prune_cache(message_cache, now, MESSAGE_CACHE_TTL_SECONDS)
    if message_id in message_cache:
        return True
    message_cache[message_id] = now
    return False


def _is_rate_limited(key: str) -> bool:
    now = time.time()
    timestamps = rate_limit_cache.get(key, [])
    timestamps = [ts for ts in timestamps if now - ts < RATE_LIMIT_WINDOW_SECONDS]
    if len(timestamps) >= RATE_LIMIT_MAX_EVENTS:
        rate_limit_cache[key] = timestamps
        return True
    timestamps.append(now)
    rate_limit_cache[key] = timestamps
    return False


def _prune_cache(cache: dict[str, float], now: float, ttl: int) -> None:
    for key, value in list(cache.items()):
        if now - value > ttl:
            cache.pop(key, None)


def _send_reply(wa_id: str, text: str, request_id: str) -> None:
    try:
        send_text_message(to=wa_id, text=text)
        logger.info("Reply sent", extra={"request_id": request_id})
    except WhatsAppAPIError:
        logger.error("Failed to send reply", extra={"request_id": request_id})
