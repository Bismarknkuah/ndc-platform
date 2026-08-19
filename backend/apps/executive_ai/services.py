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
DEFAULT_MODEL = settings.AI_MODEL


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


def ground_situation_briefing(unit_name: str, ground_intelligence: dict) -> str | None:
    """Turns real, already-aggregated complaint/welfare/report data for a
    unit (see apps.analytics.services.compute_ground_intelligence) into a
    briefing for a visiting national leader - what is actually happening
    there, and what to prioritize addressing. The model only ever sees
    the real titles, descriptions, and counts already fetched from the
    database by the caller; it never has its own access to look anything
    up and must not invent problems that were not actually reported."""
    counts = ground_intelligence.get("counts", {})

    def _format_items(items, text_field, limit=8):
        lines = []
        for item in items[:limit]:
            text = item.get(text_field, "")
            snippet = text[:200] + ("..." if len(text) > 200 else "")
            lines.append(f"- [{item.get('status', 'unknown')}] {snippet}")
        return "\n".join(lines) if lines else "(none currently pending)"

    system_prompt = (
        "You brief a senior NDC party leader (the National Chairman or "
        "the Flagbearer) ahead of a visit to a specific place - a "
        "region, constituency, or branch. You are given real complaints, "
        "welfare requests, and upward reports already submitted by "
        "members and executives there. Write a concise ground briefing: "
        "1) the 3-5 most pressing issues, grounded only in what was "
        "actually reported below, 2) a short suggested response or "
        "talking point for each, 3) anything that looks like a pattern "
        "across multiple reports. Do not invent problems that were not "
        "reported. If very little was reported, say so plainly rather "
        "than padding the briefing."
    )
    user_prompt = (
        f"Location: {unit_name}\n\n"
        f"Pending complaints ({counts.get('pending_complaints', 0)} total, "
        f"showing most recent):\n"
        f"{_format_items(ground_intelligence.get('recent_complaints', []), 'description')}\n\n"
        f"Pending welfare requests ({counts.get('pending_welfare_requests', 0)} total):\n"
        f"{_format_items(ground_intelligence.get('recent_welfare_requests', []), 'description')}\n\n"
        f"Recent upward reports ({counts.get('total_reports', 0)} total):\n"
        f"{_format_items(ground_intelligence.get('recent_reports', []), 'body')}\n\n"
        f"Pending disciplinary cases: {counts.get('pending_discipline_cases', 0)}"
    )
    return _call_claude(system_prompt, user_prompt, max_tokens=900)


def generate_official_report(
    unit_name: str, ground_intelligence: dict, include_names: bool
) -> str | None:
    """
    Two genuinely different outputs, not one report with names
    toggled by instruction: when include_names is False, reporter
    identity is stripped from the data BEFORE it ever reaches the
    model, not merely asked to be omitted - a model can be told not to
    mention something and still slip, but it cannot mention a name it
    was never given. When True, the real names already present in
    ground_intelligence (see apps.analytics.services.
    compute_ground_intelligence) are passed through as-is.
    """
    counts = ground_intelligence.get("counts", {})
    complaints = ground_intelligence.get("recent_complaints", [])

    def _format_complaint(item):
        base = f"- [{item.get('status', 'unknown')}] {item.get('subject', '')}: {item.get('description', '')[:300]}"
        if include_names:
            reporter = item.get("reported_by", "Unknown")
            base += f" (reported by {reporter})"
            if item.get("reported_executive"):
                base += f" (concerning {item['reported_executive']})"
        return base

    complaint_lines = (
        "\n".join(_format_complaint(c) for c in complaints) or "(none pending)"
    )

    system_prompt = (
        "You write a formal official report for NDC national leadership, "
        "summarizing real complaints, welfare requests, and reports "
        "submitted from a specific unit. Structure it with a short "
        "executive summary, a numbered list of issues by priority, and "
        "a closing recommendations section. Base every claim only on "
        "the data provided below - never invent details. "
        + (
            "Reporter names are included in the source data; attribute "
            "specific issues to specific reporters where relevant."
            if include_names
            else "Reporter identities have been withheld from you entirely "
            "- do not speculate about who filed anything, and do not "
            "refer to any reporter by name since you were not given any."
        )
    )
    user_prompt = (
        f"Unit: {unit_name}\n\n"
        f"Complaints and accountability reports "
        f"({counts.get('pending_complaints', 0)} pending):\n{complaint_lines}\n\n"
        f"Pending welfare requests: {counts.get('pending_welfare_requests', 0)}\n"
        f"Pending discipline cases: {counts.get('pending_discipline_cases', 0)}\n"
        f"Total upward reports: {counts.get('total_reports', 0)}"
    )
    return _call_claude(system_prompt, user_prompt, max_tokens=1200)


def generate_speech(
    unit_name: str, ground_intelligence: dict, style_instructions: str
) -> str | None:
    """A speech draft grounded in the same real ground intelligence data,
    for the party leader to deliver during or ahead of a visit -
    never a generic speech, always anchored to what was actually
    reported from this specific place. Reporter names are always
    withheld here regardless of any style instruction, since a public
    speech is exactly the wrong place to name a reporter even if the
    leader has reveal authority elsewhere."""
    counts = ground_intelligence.get("counts", {})
    complaints = ground_intelligence.get("recent_complaints", [])
    complaint_lines = (
        "\n".join(
            f"- {c.get('subject', '')}: {c.get('description', '')[:250]}"
            for c in complaints
        )
        or "(nothing specific currently pending)"
    )

    system_prompt = (
        "You draft a speech for the leader of the NDC party to deliver "
        "in or about a specific place, grounded in real issues actually "
        "reported from there. Acknowledge the real concerns below in "
        "the speech without naming any individual reporter under any "
        "circumstances - speak about the issues themselves, not who "
        "raised them. Follow the requested style/tone closely. Do not "
        "invent statistics or claims beyond what is given."
    )
    user_prompt = (
        f"Location: {unit_name}\n\n"
        f"Real issues reported from this area:\n{complaint_lines}\n\n"
        f"Pending welfare requests: {counts.get('pending_welfare_requests', 0)}\n\n"
        f"Requested style/tone: {style_instructions or 'A warm, direct campaign speech, plain language.'}"
    )
    return _call_claude(system_prompt, user_prompt, max_tokens=1400)
