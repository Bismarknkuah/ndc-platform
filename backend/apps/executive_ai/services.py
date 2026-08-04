"""
The Executive AI Assistant: a small, curated set of AI-powered tools
surfaced only to real executives (same "hierarchy.manage" authority gate
used throughout the platform), distinct from the general-purpose
platform chatbot (apps.chatbot) available to every member.

Deliberately narrow rather than a general-purpose "ask anything" agent:
three concrete tools that map to real recurring executive work
(drafting a broadcast, triaging a backlog of pending items, planning a
meeting), each with its own tightly-scoped system prompt rather than one
broad assistant that might wander into fabricating party data. Like the
platform chatbot, no tool use / function calling and no live database
access is given to the model - only whatever specific, already-fetched
context each view passes in explicitly.
"""

import logging

from django.conf import settings

logger = logging.getLogger("ndc")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-5"


def _call_claude(
    system_prompt: str, user_prompt: str, max_tokens: int = 800
) -> str | None:
    """Shared single-turn call used by all three tools below. Returns the
    reply text, or None if the AI provider isn't configured or the call
    fails - callers must surface that as a clear "unavailable" response,
    never substitute a canned/fake result for what would otherwise be a
    real generated draft."""
    if not settings.ANTHROPIC_API_KEY:
        logger.info("Executive AI tool skipped (ANTHROPIC_API_KEY not configured)")
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
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
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
        logger.exception("Executive AI tool call failed")
        return None


def draft_broadcast(user, topic: str, tone: str = "formal") -> str | None:
    """Draft a broadcast message ready for the executive to review/edit
    before actually sending via the real Broadcast feature (this tool
    only drafts text - it never sends anything itself)."""
    unit_name = (
        user.organizational_unit.name if user.organizational_unit else "the Party"
    )
    system_prompt = (
        "You draft broadcast messages for officers of the National "
        "Democratic Congress (NDC) to send to their members. Write a "
        "single, ready-to-send broadcast message: no options, no "
        "commentary, no placeholders like [insert date] left "
        "unfilled unless the topic genuinely requires information "
        f"only the officer has. Tone: {tone}. Keep it concise - a "
        "broadcast, not an essay."
    )
    user_prompt = f"Officer's unit: {unit_name}\nTopic/brief for the broadcast: {topic}"
    return _call_claude(system_prompt, user_prompt, max_tokens=500)


def summarize_pending_items(user, jurisdiction_summary: dict) -> str | None:
    """Turn the raw pending-item counts from the dashboard's jurisdiction
    rollup into a short, prioritized action summary - the model only
    ever sees the counts already computed and passed in by the view, not
    live database access of its own."""
    system_prompt = (
        "You help NDC party executives triage their pending workload. "
        "Given counts of pending complaints, disciplinary cases, and "
        "welfare requests across their jurisdiction, write a short "
        "(3-5 sentence) prioritized summary of what needs attention "
        "and suggest a sensible order to address them in. Do not "
        "invent specific case details you weren't given - work only "
        "from the counts provided."
    )
    user_prompt = (
        f"Jurisdiction: {jurisdiction_summary.get('organizational_unit', {}).get('name', 'Unknown')}\n"
        f"Pending complaints: {jurisdiction_summary.get('pending_complaints', 0)}\n"
        f"Pending disciplinary cases: {jurisdiction_summary.get('pending_discipline_cases', 0)}\n"
        f"Pending welfare requests: {jurisdiction_summary.get('pending_welfare_requests', 0)}\n"
        f"Total members in jurisdiction: {jurisdiction_summary.get('total_members', 0)}"
    )
    return _call_claude(system_prompt, user_prompt, max_tokens=400)


def generate_meeting_agenda(user, meeting_topic: str, context: str = "") -> str | None:
    """Generate a structured meeting agenda from a topic and optional
    free-text context the officer provides."""
    unit_name = (
        user.organizational_unit.name if user.organizational_unit else "the Party"
    )
    system_prompt = (
        "You draft meeting agendas for NDC party officers. Given a "
        "meeting topic and optional context, produce a clear, "
        "numbered agenda with realistic time allocations (assume a "
        "60-90 minute meeting unless context suggests otherwise). "
        "Include a brief opening (welcome/roll call) and closing "
        "(AOB/next steps) item. No commentary before or after the "
        "agenda itself."
    )
    user_prompt = f"Unit: {unit_name}\nMeeting topic: {meeting_topic}"
    if context:
        user_prompt += f"\nAdditional context: {context}"
    return _call_claude(system_prompt, user_prompt, max_tokens=600)
