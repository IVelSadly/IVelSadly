from __future__ import annotations

from typing import Any

import httpx

from .config import settings

GRAPH_API_BASE_URL = "https://graph.facebook.com/v18.0"


class WhatsAppAPIError(RuntimeError):
    pass


def _ensure_configured() -> None:
    if not settings.whatsapp_access_token:
        raise WhatsAppAPIError("WHATSAPP_ACCESS_TOKEN is not set.")
    if not settings.whatsapp_phone_number_id:
        raise WhatsAppAPIError("WHATSAPP_PHONE_NUMBER_ID is not set.")


def send_text_message(*, to: str, text: str) -> dict[str, Any]:
    _ensure_configured()

    url = f"{GRAPH_API_BASE_URL}/{settings.whatsapp_phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text},
    }

    with httpx.Client(timeout=10) as client:
        response = client.post(url, headers=headers, json=payload)

    if response.is_error:
        raise WhatsAppAPIError(
            f"Graph API error {response.status_code}: {response.text}"
        )

    return response.json()
