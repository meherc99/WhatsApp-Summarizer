"""Apify-based WhatsApp chat scraper."""

import json
import os

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
# Override APIFY_ACTOR_ID in .env to use a different WhatsApp actor
ACTOR_ID = os.getenv("APIFY_ACTOR_ID", "extremescrapes/whatsapp-messages-scraper")


def scrape(chat_id: str, max_messages: int = 100) -> list[dict]:
    """Run the configured Apify WhatsApp actor and return normalized messages.

    The actor is determined by APIFY_ACTOR_ID in .env.
    Input can be fully overridden via APIFY_ACTOR_INPUT_JSON for actor-specific schemas.
    """
    if not APIFY_TOKEN:
        raise ValueError("APIFY_API_TOKEN not set in environment")

    client = ApifyClient(APIFY_TOKEN)

    custom_input = os.getenv("APIFY_ACTOR_INPUT_JSON")
    if custom_input:
        actor_input = json.loads(custom_input)
    else:
        actor_input = {
            "chatId": chat_id,
            "maxMessages": max_messages,
        }

    print(f"[apify] Starting actor '{ACTOR_ID}' for chat: {chat_id}")
    run = client.actor(ACTOR_ID).call(run_input=actor_input)

    raw = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"[apify] Retrieved {len(raw)} raw items")

    messages = [_normalize(item) for item in raw]
    # Drop items with no message body
    messages = [m for m in messages if m["message"].strip()]
    print(f"[apify] {len(messages)} messages after filtering")
    return messages


def _normalize(raw: dict) -> dict:
    """Map actor-specific output keys to the internal {sender, message, datetime} format.

    Tries common key names used by different WhatsApp actors on Apify.
    """
    return {
        "sender": (
            raw.get("author")
            or raw.get("from")
            or raw.get("sender")
            or raw.get("pushname")
            or "Unknown"
        ),
        "message": (
            raw.get("body")
            or raw.get("text")
            or raw.get("message")
            or raw.get("content")
            or ""
        ),
        "datetime": (
            raw.get("timestamp")
            or raw.get("date")
            or raw.get("datetime")
            or raw.get("t")
            or ""
        ),
    }
