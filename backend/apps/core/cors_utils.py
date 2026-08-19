def normalize_cors_origin(raw_origin: str) -> str:
    """Fixes the two mistakes that keep showing up in a pasted
    CORS_ALLOWED_ORIGINS value: a missing scheme prefix (a bare domain
    like "ndc-platform.vercel.app" instead of
    "https://ndc-platform.vercel.app") and a doubled scheme letter from
    a typo (e.g. "hhttps://..."). django-cors-headers does exact string
    matching against the browser's real Origin header, which always
    includes a correct scheme, so either mistake here silently breaks
    matching with no error at Django startup - the request just fails
    at the browser with a CORS error and no useful server-side log.
    """
    origin = raw_origin.strip().rstrip("/")
    while origin.lower().startswith("h") and not origin.lower().startswith("http"):
        origin = origin[1:]
    if origin and not origin.startswith(("http://", "https://")):
        origin = "https://" + origin
    return origin
