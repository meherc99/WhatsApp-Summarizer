"""OpenAI-based WhatsApp chat summarizer."""

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_SENDER_MAPPING: dict[str, str] = {}
_client: OpenAI | None = None

SYSTEM_PROMPT = """Summarize the following WhatsApp group chat. Senders have been anonymized as A, B, C, etc.

Structure your summary into these sections (skip any section with nothing relevant):
- **Announcements**: Important notices shared with the group
- **Questions & Clarifications**: For each topic, include a title and bullet-pointed summary of the discussion and final answer
- **General Discussion**: Key themes and topics talked about
- **Action Items**: Tasks or follow-ups anyone committed to
- **Links & Resources**: Any URLs or references shared
- **Other**: Anything that doesn't fit the above

Be concise. Use bullet points within sections."""


def summarize(messages: list[dict], group_name: str = "") -> str:
    """Summarize a list of {sender, message, datetime} dicts.

    Senders are anonymized to single letters before sending to the model.
    Returns the summary as a string.
    """
    _SENDER_MAPPING.clear()

    chat_lines = [
        f"{_encode_sender(m['sender'])}: {m['message']}"
        for m in messages
        if m.get("message", "").strip()
    ]

    if not chat_lines:
        return "No messages to summarize."

    chat_text = "\n".join(chat_lines)

    system = SYSTEM_PROMPT
    if group_name:
        system = f"Group: **{group_name}**\n\n" + system

    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": chat_text},
        ],
        temperature=0.1,
    )
    return response.choices[0].message.content


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        _client = OpenAI(api_key=api_key)
    return _client


def _encode_sender(sender: str) -> str:
    if sender not in _SENDER_MAPPING:
        last = list(_SENDER_MAPPING.values())
        _SENDER_MAPPING[sender] = chr(ord(last[-1]) + 1) if last else "A"
    return _SENDER_MAPPING[sender]
