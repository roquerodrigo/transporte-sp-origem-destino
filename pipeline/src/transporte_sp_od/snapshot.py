"""Raw snapshot storage.

Every source's bytes are stored under ``data/raw/<source>/<YYYY-MM-DD>/`` next to a
``manifest.json`` (url, sha256, fetch time) before anything parses them, so a build is
reproducible from the repository. The payloads are large (the survey alone is 198 MB) and
are not committed; the manifests are.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, date, datetime
from pathlib import Path

import httpx

from transporte_sp_od.config import settings

log = logging.getLogger(__name__)


def snapshot_dir(source: str, on: date | None = None) -> Path:
    return settings.raw_dir / source / (on or datetime.now(UTC).date()).isoformat()


def latest_snapshot(source: str) -> Path | None:
    root = settings.raw_dir / source
    if not root.is_dir():
        return None
    dated = sorted(path for path in root.iterdir() if path.is_dir())
    return dated[-1] if dated else None


def write(source: str, filename: str, payload: bytes, url: str, licence: str) -> Path:
    directory = snapshot_dir(source)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    target.write_bytes(payload)

    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest[filename] = {
        "url": url,
        "licence": licence,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    log.info("%s: stored %s (%.1f MB)", source, filename, len(payload) / 1e6)
    return target


def path(source: str, filename: str) -> Path:
    """Absolute path to *filename* in the latest snapshot of *source*."""
    directory = latest_snapshot(source)
    if directory is None:
        raise FileNotFoundError(f"no snapshot for {source!r}; run `transporte-sp-od fetch` first")
    target = directory / filename
    if not target.exists():
        raise FileNotFoundError(f"{target} missing from the {source!r} snapshot")
    return target


def fetched_on(source: str) -> date:
    directory = latest_snapshot(source)
    return date.fromisoformat(directory.name) if directory else datetime.now(UTC).date()


def download(url: str) -> bytes:
    headers = {"User-Agent": settings.user_agent}
    last_error: Exception | None = None
    for attempt in range(1, settings.http_retries + 1):
        try:
            with httpx.Client(timeout=settings.http_timeout, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as error:  # noqa: BLE001 - retried, re-raised on exhaustion
            last_error = error
            log.warning("%s attempt %d/%d failed: %s", url, attempt, settings.http_retries, error)
    raise RuntimeError(f"failed to download {url}") from last_error
