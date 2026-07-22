"""Shared HTTP session configuration."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


USER_AGENT = (
    "Mozilla/5.0 (compatible; AcademicResearchBot/1.0; "
    "+local-master-thesis-data-collection)"
)


def create_http_session(retry_count: int = 2) -> requests.Session:
    """Create a session with small, backoff-based transient-error retries."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=retry_count,
        connect=retry_count,
        read=retry_count,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
