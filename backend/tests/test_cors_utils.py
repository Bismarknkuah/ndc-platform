from apps.core.cors_utils import normalize_cors_origin


def test_fixes_doubled_scheme_letter_typo():
    """The exact typo pasted in a real Railway CORS_ALLOWED_ORIGINS value:
    "hhttps://..." instead of "https://..."."""
    assert (
        normalize_cors_origin("hhttps://ndc-platform.vercel.app")
        == "https://ndc-platform.vercel.app"
    )


def test_fixes_missing_scheme_entirely():
    """Also seen in a real pasted value: a bare domain with no
    http:// or https:// prefix at all."""
    assert (
        normalize_cors_origin(
            "ndc-platform-git-main-desward-technology-s-projects.vercel.app"
        )
        == "https://ndc-platform-git-main-desward-technology-s-projects.vercel.app"
    )


def test_leaves_a_correctly_formed_origin_unchanged():
    assert (
        normalize_cors_origin("https://ndc-platform.vercel.app")
        == "https://ndc-platform.vercel.app"
    )
    assert normalize_cors_origin("http://localhost:3000") == "http://localhost:3000"


def test_strips_surrounding_whitespace_and_trailing_slash():
    assert (
        normalize_cors_origin("  https://ndc-platform.vercel.app/  ")
        == "https://ndc-platform.vercel.app"
    )


def test_handles_triple_doubled_letter_typo():
    assert (
        normalize_cors_origin("hhhttps://ndc-platform.vercel.app")
        == "https://ndc-platform.vercel.app"
    )


def test_cors_allowed_origins_setting_actually_gets_normalized():
    """End-to-end: the exact malformed value pasted for a real Railway
    deployment, run through the real settings.py parsing logic, not
    just the utility function in isolation."""
    import importlib
    import os

    original = os.environ.get("CORS_ALLOWED_ORIGINS")
    os.environ["CORS_ALLOWED_ORIGINS"] = (
        "hhttps://ndc-platform.vercel.app,"
        "ndc-platform-git-main-desward-technology-s-projects.vercel.app"
    )
    try:
        from config import settings

        importlib.reload(settings)
        assert "https://ndc-platform.vercel.app" in settings.CORS_ALLOWED_ORIGINS
        assert (
            "https://ndc-platform-git-main-desward-technology-s-projects.vercel.app"
            in settings.CORS_ALLOWED_ORIGINS
        )
    finally:
        if original is None:
            os.environ.pop("CORS_ALLOWED_ORIGINS", None)
        else:
            os.environ["CORS_ALLOWED_ORIGINS"] = original
        importlib.reload(settings)
