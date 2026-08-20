"""
Rule-based fallbacks for every Executive AI tool, used automatically
whenever ANTHROPIC_API_KEY isn't configured, so the platform's AI
features work out of the box with zero external dependency rather than
returning "unavailable" until someone sets up billing on a real
Anthropic account.

These are deliberately NOT trying to imitate an LLM's free-form prose -
that would risk exactly the "canned/fake result" problem the real AI
tools' docstrings warn against. Instead, each one is an honest,
clearly-labeled, deterministic summary or template built directly from
real data, using plain conditional logic (counts, sorting, simple
category rules) rather than natural language generation. Every response
this module produces is paired with source="rule_based" so the caller
can label it honestly in the UI - never presented as if it came from
Claude.

If ANTHROPIC_API_KEY is later configured, every one of these tools
automatically switches to the real AI version with no further changes -
see the source="ai" | "rule_based" branch in each executive_ai view.
"""

import datetime


def _days_ago(iso_timestamp: str) -> int:
    try:
        created = datetime.datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        now = (
            datetime.datetime.now(created.tzinfo)
            if created.tzinfo
            else datetime.datetime.utcnow()
        )
        return (now - created).days
    except (ValueError, TypeError):
        return 0


def fallback_draft_broadcast(unit_name: str, topic: str, tone: str = "formal") -> str:
    opener = {
        "formal": f"Dear members of {unit_name},",
        "urgent": f"URGENT NOTICE - {unit_name}",
        "friendly": f"Hello everyone in {unit_name},",
    }.get(tone.lower(), f"Dear members of {unit_name},")

    return (
        f"{opener}\n\n"
        f"{topic}\n\n"
        "[Add any specific dates, venues, or figures only you have before sending.]\n\n"
        "Thank you for your continued commitment to the party.\n\n"
        "-- NDC Leadership"
    )


def fallback_summarize_pending_items(jurisdiction_summary: dict) -> str:
    unit_name = jurisdiction_summary.get("organizational_unit", {}).get(
        "name", "your jurisdiction"
    )
    complaints = jurisdiction_summary.get("pending_complaints", 0)
    discipline = jurisdiction_summary.get("pending_discipline_cases", 0)
    welfare = jurisdiction_summary.get("pending_welfare_requests", 0)
    total_members = jurisdiction_summary.get("total_members", 0)

    items = [
        ("disciplinary cases", discipline, 3),
        ("complaints", complaints, 2),
        ("welfare requests", welfare, 1),
    ]
    pending_items = [
        (name, count, weight) for name, count, weight in items if count > 0
    ]
    pending_items.sort(key=lambda x: x[1] * x[2], reverse=True)

    if not pending_items:
        return f"Nothing pending in {unit_name} right now ({total_members} members). A clear inbox."

    lines = [f"Pending workload in {unit_name} ({total_members} members):"]
    for i, (name, count, _weight) in enumerate(pending_items, start=1):
        lines.append(f"{i}. {count} {name}")
    if discipline > 0:
        lines.append(
            "Disciplinary cases carry the most time-sensitivity given natural-justice "
            "timelines - address these first."
        )
    elif complaints > 0:
        lines.append("Complaints should generally be triaged before welfare requests.")
    return "\n".join(lines)


def fallback_meeting_agenda(
    unit_name: str, meeting_topic: str, context: str = ""
) -> str:
    lines = [
        f"Meeting Agenda: {meeting_topic}",
        f"Unit: {unit_name}",
        "",
        "1. Welcome and roll call (5 min)",
        "2. Adoption of previous minutes (5 min)",
        f"3. {meeting_topic} - main discussion (30-40 min)",
    ]
    if context:
        lines.append(f"   Context: {context}")
    lines += [
        "4. Questions and open floor (10-15 min)",
        "5. Action items and responsible officers (10 min)",
        "6. Any other business (5 min)",
        "7. Closing remarks and next meeting date (5 min)",
    ]
    return "\n".join(lines)


def fallback_ground_briefing(unit_name: str, ground_intelligence: dict) -> str:
    counts = ground_intelligence.get("counts", {})
    complaints = ground_intelligence.get("recent_complaints", [])
    welfare = ground_intelligence.get("recent_welfare_requests", [])

    lines = [f"Ground summary for {unit_name} (data-driven, AI unavailable):", ""]
    lines.append(
        f"{counts.get('pending_complaints', 0)} pending complaints, "
        f"{counts.get('pending_welfare_requests', 0)} welfare requests, "
        f"{counts.get('pending_discipline_cases', 0)} discipline cases, "
        f"{counts.get('total_reports', 0)} reports on file."
    )

    if complaints:
        oldest = sorted(complaints, key=lambda c: c.get("created_at", ""))[:3]
        lines.append("\nOldest pending complaints (address these first):")
        for c in oldest:
            days = _days_ago(c.get("created_at", ""))
            age = f"{days} day{'s' if days != 1 else ''} old" if days else "recent"
            lines.append(f"- {c.get('subject', 'Untitled')} ({age})")

    if welfare:
        lines.append("\nPending welfare requests:")
        for w in welfare[:3]:
            lines.append(
                f"- {w.get('category', 'Other')}: {w.get('description', '')[:100]}"
            )

    if not complaints and not welfare:
        lines.append("\nNothing specific currently pending here.")

    return "\n".join(lines)


def fallback_official_report(
    unit_name: str, ground_intelligence: dict, include_names: bool
) -> str:
    counts = ground_intelligence.get("counts", {})
    complaints = ground_intelligence.get("recent_complaints", [])

    lines = [
        f"OFFICIAL REPORT: {unit_name}",
        f"Generated (data-driven, AI unavailable) - {datetime.datetime.utcnow().strftime('%Y-%m-%d')}",
        "",
        "Summary:",
        f"- {counts.get('pending_complaints', 0)} pending complaints",
        f"- {counts.get('pending_welfare_requests', 0)} pending welfare requests",
        f"- {counts.get('pending_discipline_cases', 0)} pending discipline cases",
        f"- {counts.get('total_reports', 0)} upward reports on file",
        "",
        "Issues, oldest first:",
    ]
    ordered = sorted(complaints, key=lambda c: c.get("created_at", ""))
    for i, c in enumerate(ordered, start=1):
        entry = f"{i}. [{c.get('status', 'unknown')}] {c.get('subject', 'Untitled')}"
        if include_names and c.get("reported_by"):
            entry += f" - reported by {c['reported_by']}"
        lines.append(entry)
        if c.get("description"):
            lines.append(f"   {c['description'][:200]}")
    if not ordered:
        lines.append("(none pending)")

    lines += [
        "",
        "Recommendation: address items above in the order listed, oldest first, "
        "since age is the only prioritization signal available without AI analysis.",
    ]
    return "\n".join(lines)


def fallback_speech(
    unit_name: str, ground_intelligence: dict, style_instructions: str = ""
) -> str:
    complaints = ground_intelligence.get("recent_complaints", [])
    lines = [
        f"[Speech notes for {unit_name} - template, AI unavailable]",
        "",
        f"Thank you for having me here in {unit_name}.",
        "",
    ]
    if complaints:
        lines.append(
            "I want to acknowledge some of the real concerns raised here recently:"
        )
        for c in complaints[:3]:
            lines.append(f"- {c.get('subject', 'a concern raised locally')}")
        lines.append("\nWe hear you, and we are committed to following up on these.")
    else:
        lines.append(
            "I don't have specific local issues on file to reference here yet."
        )
    lines.append(
        f"\n[Requested style noted: {style_instructions or 'none specified'} - "
        "adjust tone manually, this template doesn't apply style automatically.]"
    )
    return "\n".join(lines)
