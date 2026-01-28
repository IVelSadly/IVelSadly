from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from .config import settings
from .whatsapp import WhatsAppAPIError, send_text_message

app = FastAPI(title="WhatsApp Bot MVP - Passo 1")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


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
async def receive_webhook(request: Request) -> dict[str, Any]:
    payload = await request.json()

    entry = (payload.get("entry") or [None])[0]
    changes = (entry or {}).get("changes") or []
    value = (changes[0] or {}).get("value") if changes else {}
    messages = value.get("messages") or []

    if not messages:
        return {"status": "ignored", "reason": "no_messages"}

    message = messages[0]
    if message.get("type") != "text":
        return {"status": "ignored", "reason": "non_text_message"}

    text_body = ((message.get("text") or {}).get("body") or "").strip()
    if not text_body:
        return {"status": "ignored", "reason": "empty_text"}

    wa_id = message.get("from") or ((value.get("contacts") or [{}])[0]).get("wa_id")
    if not wa_id:
        return {"status": "ignored", "reason": "missing_wa_id"}

    try:
        send_text_message(to=wa_id, text=f"Recebido: {text_body}")
    except WhatsAppAPIError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return {"status": "sent", "to": wa_id}
