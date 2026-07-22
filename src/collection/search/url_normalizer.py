"""Conservative URL normalization for article-link deduplication."""

from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit


TRACKING_PARAMETERS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
    }
)


def normalize_url(
    url: str,
    base_url: str,
    expected_domain: str | None = None,
) -> str | None:
    """Make an absolute canonical URL, or return ``None`` for another domain."""
    try:
        absolute_url = urljoin(base_url, url.strip())
        parsed = urlsplit(absolute_url)
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None

    hostname = parsed.hostname.lower().rstrip(".")
    if expected_domain:
        expected = expected_domain.lower().rstrip(".")
        if hostname != expected and not hostname.endswith(f".{expected}"):
            return None

    if port and not (
        (parsed.scheme.lower() == "http" and port == 80)
        or (parsed.scheme.lower() == "https" and port == 443)
    ):
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMETERS
    ]
    return urlunsplit(
        (parsed.scheme.lower(), netloc, path, urlencode(query_items, doseq=True), "")
    )
