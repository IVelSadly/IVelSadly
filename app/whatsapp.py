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

    timeout = httpx.Timeout(10.0, connect=5.0)
    transport = httpx.HTTPTransport(retries=2)

    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as error:
        raise WhatsAppAPIError("Graph API request failed.") from error

    return response.json()
