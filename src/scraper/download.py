"""Descarga del HTML original (tal cual) de una providencia individual."""

from __future__ import annotations

import logging
import re

from src.scraper.client import RateLimitedClient

logger = logging.getLogger(__name__)

_RE_CHARSET = re.compile(rb"charset=([a-zA-Z0-9_-]+)", re.IGNORECASE)


def descargar_html_providencia(client: RateLimitedClient, url: str) -> bytes:
    """Descarga y devuelve los bytes originales del HTML de la providencia,
    sin transcodificar (el sitio publica estos documentos en windows-1252)."""
    response = client.get(url)
    return response.content


def detectar_encoding(contenido: bytes, default: str = "windows-1252") -> str:
    match = _RE_CHARSET.search(contenido)
    if match:
        return match.group(1).decode("ascii", errors="ignore")
    return default


def decodificar_para_lectura(contenido: bytes) -> str:
    """Decodifica el HTML solo para lectura/clasificación (el archivo guardado
    en disco conserva siempre los bytes originales)."""
    encoding = detectar_encoding(contenido)
    try:
        return contenido.decode(encoding, errors="replace")
    except LookupError:
        return contenido.decode("windows-1252", errors="replace")
