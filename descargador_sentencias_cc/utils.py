"""Utilidades pequeñas compartidas: normalización de texto y slugs para rutas de archivo."""

from __future__ import annotations

import re
import unicodedata


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def normalize_key(text: str) -> str:
    """Normaliza texto para comparar encabezados/etiquetas sin importar acentos, mayúsculas o espacios."""
    return re.sub(r"[^a-z0-9]+", "", strip_accents(text).lower())


def slugify(text: str, default: str = "sin-clasificar") -> str:
    """Convierte texto libre en un slug apto para nombres de carpeta/archivo."""
    if not text:
        return default
    text = strip_accents(text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or default
