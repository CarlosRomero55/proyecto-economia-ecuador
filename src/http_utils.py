"""Descargas HTTP con reintentos, backoff exponencial y caché local en data/raw."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

from src import config

log = config.get_logger("http")
USER_AGENT = "ecuador-trade-economy-monitor/1.0 (portfolio project)"


def _cache_path(url: str, params: dict | None, subdir: str, suffix: str) -> Path:
    key = hashlib.sha1((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()[:16]
    folder = config.DATA_RAW / subdir
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{key}{suffix}"


def get(url: str, params: dict | None = None, *, subdir: str, suffix: str = ".json",
        retries: int = 5, backoff: float = 2.0, use_cache: bool = True, timeout: int = 60) -> bytes:
    """GET con caché. Reintenta en errores de red, 429 y 5xx con espera exponencial."""
    cache = _cache_path(url, params, subdir, suffix)
    if use_cache and cache.exists():
        return cache.read_bytes()
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            cache.write_bytes(r.content)
            return r.content
        except (requests.RequestException, requests.HTTPError) as err:
            last_err = err
            wait = backoff ** attempt
            log.warning("Intento %s/%s falló (%s). Reintento en %.0fs", attempt, retries, err, wait)
            time.sleep(wait)
    raise RuntimeError(f"No se pudo descargar {url}: {last_err}")
