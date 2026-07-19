# Intentionally weak SSRF defense fixture for security-review evals. Do not deploy.
from urllib.parse import urlparse

import requests

ALLOWED_HOSTS = {"hooks.example.com", "api.partner.example"}


def fetch_webhook(url: str) -> bytes:
    host = urlparse(url).hostname
    if host not in ALLOWED_HOSTS:
        raise ValueError("host not allowed")
    # Follows redirects; does not re-check the final hop or resolved IPs.
    response = requests.get(url, timeout=10, allow_redirects=True)
    response.raise_for_status()
    return response.content
