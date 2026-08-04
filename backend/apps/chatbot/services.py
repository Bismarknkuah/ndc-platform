"""
The platform assistant: a conversational Q&A helper available to every
member regardless of role, meant to answer "how do I..." and "what is
the process for..." questions about using the NDC Platform and general
questions about how the party is organized.

Deliberately scoped for safety:
- No tool use / function calling and no database access is given to the
  model - it only ever sees the conversation history plus the calling
  user's own basic profile (name, role, organizational unit) for
  personalization. It cannot look up or discuss anyone else's data,
  because it is never given the means to.
- Uses the same ANTHROPIC_API_KEY configuration as AI-assisted reporting
  (apps.analytics.ai_reporting) - if unset, generate_chat_reply returns
  None and the view surfaces a clear 503 rather than a fake reply.
"""

import logging

from django.conf import settings

from apps.chatbot.constants import MAX_HISTORY_MESSAGES

logger = logging.getLogger("ndc")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-5"

SYSTEM_PROMPT_TEMPLATE = """You are the NDC Platform Assistant, a help \
assistant embedded in the National Democratic Congress's party \
management system. You are talking with {full_name}, whose role is \
{role_name} at {unit_name}.

You can help with:
- How to use the platform: navigating hierarchy, members, departments, \
messaging, elections, finance, donations, welfare, complaints, events, \
documents, media, analytics, and settings.
- General questions about how the party's structure and processes work \
(the constitutional hierarchy from National down to Branch, TEIN, \
auxiliary wings, departments, elections, and so on).
- Plain civic/political-process questions unrelated to anyone's private \
data.

You do not have access to any member's private data, financial records, \
or any database beyond this conversation and the profile info given \
above - never claim to look something up, and never invent specific \
figures, names, or records. If asked something that requires real \
platform data (e.g. "how many members do we have"), tell the person \
which screen shows that (e.g. "check the Analytics page") rather than \
guessing a number.

Keep answers concise and practical. Plain prose, no need for headers.
"""


def _build_system_prompt(user) -> str:
    role_name = user.role.name if user.role else "Ordinary Member"
    unit_name = (
        user.organizational_unit.name
        if user.organizational_unit
        else "no assigned unit"
    )
    return SYSTEM_PROMPT_TEMPLATE.format(
        full_name=user.full_name, role_name=role_name, unit_name=unit_name
    )


def generate_chat_reply(user, history: list[dict]) -> str | None:
    """
    `history` is a list of {"role": "user"|"assistant", "body": str}
    dicts in chronological order, ending with the newest user message.
    Returns the assistant's reply text, or None if the AI provider isn't
    configured or the call fails - callers must surface that as a clear
    "unavailable" response, never substitute a canned/fake reply.
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.info("Chat reply skipped (ANTHROPIC_API_KEY not configured)")
        return None

    trimmed_history = history[-MAX_HISTORY_MESSAGES:]
    messages = [
        {
            "role": "assistant" if m["role"] == "ASSISTANT" else "user",
            "content": m["body"],
        }
        for m in trimmed_history
    ]
    if not messages or messages[-1]["role"] != "user":
        # The Anthropic API requires the turn sequence to end on a user
        # message - this should never happen given how the view calls
        # this, but fail loudly rather than send a malformed request.
        logger.error("generate_chat_reply called without a trailing user message")
        return None

    try:
        import requests

        response = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": ANTHROPIC_API_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": DEFAULT_MODEL,
                "max_tokens": 600,
                "system": _build_system_prompt(user),
                "messages": messages,
            },
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        text_blocks = [
            block["text"]
            for block in body.get("content", [])
            if block.get("type") == "text"
        ]
        return "\n".join(text_blocks).strip() or None
    except Exception:
        logger.exception("Chat reply generation failed for user=%s", user.id)
        return None
