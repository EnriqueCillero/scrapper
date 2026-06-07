from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


def safe_basename_from_url(url: str | None) -> str | None:
    if not url:
        return None
    base = url.split('?', 1)[0].split('#', 1)[0].rstrip('/').split('/')[-1]
    return base or None


def safe_filename(name: str) -> str:
    name = (name or '').strip()
    name = ''.join(ch if ch.isalnum() or ch in {'.', '-', '_'} else '_' for ch in name)
    name = name.strip('._-') or 'asset'
    return name


def download_via_fetch(locator: Any, url: str) -> bytes | None:
    page = getattr(locator, 'page', None)
    if page is not None and isinstance(url, str):
        u = url.strip()
        if u and not (u.startswith('data:') or u.startswith('blob:')):
            try:
                resolved = u
                if not (resolved.startswith('http://') or resolved.startswith('https://')):
                    resolved = urljoin(getattr(page, 'url', '') or '', resolved)
                resp = page.request.get(resolved, timeout=30_000)
                if getattr(resp, 'ok', False):
                    return resp.body()
            except Exception:
                pass

    js = r"""
        async (el, url) => {
        const res = await fetch(url);
        if (!res.ok) return null;
        const buf = await res.arrayBuffer();
        const bytes = new Uint8Array(buf);
        let binary = '';
        const chunk = 0x8000;
        for (let i = 0; i < bytes.length; i += chunk) {
            binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
        }
        return btoa(binary);
        }
    """

    try:
        b64 = locator.evaluate(js, url)
    except Exception:
        return None
    if not b64:
        return None
    try:
        return base64.b64decode(b64)
    except Exception:
        return None


def ensure_asset(*, locator: Any, url: str, assets_dir: Path, filename: str) -> bool:
    """Download `url` into `assets_dir/filename` if missing. Logs progress."""

    assets_dir.mkdir(parents=True, exist_ok=True)
    target = assets_dir / filename

    if target.exists():
        logger.debug('Asset %s already exists, skipping download.', filename)
        return True

    logger.info('Downloading asset %s', filename)
    data = download_via_fetch(locator, url)
    if not data:
        logger.warning('Failed downloading asset %s', filename)
        return False

    target.write_bytes(data)
    logger.info('Saved asset %s (%s bytes)', filename, len(data))
    return True
