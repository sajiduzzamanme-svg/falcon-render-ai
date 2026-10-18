"""Shared HTTP client factory for render adapters.

`trust_env=False` is deliberate: some environments export NO_PROXY entries
(e.g. `*[::1]`) that crash httpx's env-proxy mount parsing with
`InvalidURL: Invalid port`. The egress proxy (when one is configured) is
passed explicitly instead, so provider calls keep working there.
"""

import os
from pathlib import Path

import httpx

# System bundle first: some environments (egress proxies with TLS
# interception) need their CA, which certifi's bundle does not include.
_SYSTEM_CA = "/etc/ssl/certs/ca-certificates.crt"


def http_client(timeout_s: float) -> httpx.Client:
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    verify: str | bool = _SYSTEM_CA if Path(_SYSTEM_CA).exists() else True
    return httpx.Client(trust_env=False, proxy=proxy, timeout=timeout_s, verify=verify)
