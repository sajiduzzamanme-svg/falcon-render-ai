"""Job store backend selection (ADR 0002).

Supabase is used when ``SUPABASE_URL`` and ``SUPABASE_SERVICE_KEY`` are both
set; otherwise the local JSON file store (local-dev fallback).

``jobs`` is a proxy that resolves the backend on every attribute access, so
tests can switch backends by monkeypatching settings — nothing is bound at
import time. Routes use ``from ..job_store import jobs`` as a drop-in
replacement for ``from .. import jobs``.
"""

from . import jobs as _json_store
from . import jobs_supabase as _supabase_store
from .supabase_client import is_configured


def get_store():
    """Return the active job store module (supabase or json)."""
    return _supabase_store if is_configured() else _json_store


class _StoreProxy:
    def __getattr__(self, name: str):
        return getattr(get_store(), name)


jobs = _StoreProxy()
