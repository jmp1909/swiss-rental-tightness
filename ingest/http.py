"""Shared HTTP fetch helper: caches downloads under data/raw/<source>/."""
import hashlib
from pathlib import Path

import requests

from .db import PROJECT_ROOT

RAW_DIR = PROJECT_ROOT / "data" / "raw"
TIMEOUT = 60


def fetch(url: str, source: str, filename: str | None = None, headers: dict | None = None) -> Path:
    """Download url into data/raw/<source>/<filename>, skipping if already cached."""
    source_dir = RAW_DIR / source
    source_dir.mkdir(parents=True, exist_ok=True)
    if filename is None:
        filename = hashlib.sha256(url.encode()).hexdigest()[:16]
    dest = source_dir / filename
    if dest.exists():
        return dest
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def fetch_bytes(url: str, headers: dict | None = None) -> bytes:
    """Fetch a URL without caching to disk (for API queries where params vary)."""
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.content


def post_json_cached(url: str, payload: dict, source: str, filename: str) -> Path:
    """POST a JSON query, caching the response body under data/raw/<source>/<filename>."""
    source_dir = RAW_DIR / source
    source_dir.mkdir(parents=True, exist_ok=True)
    dest = source_dir / filename
    if dest.exists():
        return dest
    resp = requests.post(url, json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest
