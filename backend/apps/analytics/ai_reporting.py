"""
AI-assisted reporting: turns the real aggregated stats this platform
already computes (membership analytics, department analytics, election
results, finance summaries) into a concise natural-language executive
summary, via a real call to Anthropic's Messages API. Configure
ANTHROPIC_API_KEY (see .env.example) to turn this on; without it,
generate_summary() returns None and the caller surfaces a clear "AI
reporting is not configured" response rather than faking a summary.
"""

import logging

from django.conf import settings

logger = logging.getLogger("ndc")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-4-5"


def generate_summary(report_type: str, source_data: dict) -> str | None:
    """
    Sends the already-computed stats (never raw member records - just the
    aggregates) to Claude and asks for a short executive summary a party
    officer could read in ten seconds. Returns None if ANTHROPIC_API_KEY
    isn't configured or the call fails - callers must handle that
    gracefully, never substitute a fake summary.
    """
    if not settings.ANTHROPIC_API_KEY:
        logger.info(
            "AI report skipped (ANTHROPIC_API_KEY not configured): report_type=%s",
            report_type,
        )
        return None

    prompt = (
        f"You are writing a brief executive summary for a National Democratic Congress (NDC) "
        f"party officer, based on this {report_type} report data:\n\n"
        f"{source_data}\n\n"
        f"Write 3-5 sentences highlighting the most important, actionable takeaways. "
        f"Be concrete and cite specific numbers from the data. Do not invent any figures "
        f"not present in the data. Plain prose, no headers or bullet points."
    )

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
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
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
        logger.exception("AI report generation failed: report_type=%s", report_type)
        return None
