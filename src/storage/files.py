"""Organización de archivos: /jurisprudencia/corte-constitucional/<área>/<tema>/NUMERO.htm(+_metadata.json)."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from src import config


def slugificar(texto: str, max_len: int = 80) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    texto = texto.strip("-")
    return texto[:max_len].rstrip("-") or "sin-tema"


def nombre_archivo_base(numero_providencia: str) -> str:
    # "T-388/19" -> "T-388-19"  (mismo patrón usado por el sitio de origen)
    return re.sub(r"[^A-Za-z0-9-]+", "-", numero_providencia.replace("/", "-")).strip("-")


def carpeta_destino(output_dir: Path, area_slug: str, tema_slug: str) -> Path:
    return Path(output_dir) / config.CORTE_SLUG / area_slug / tema_slug


def guardar_providencia(
    output_dir: Path,
    area_slug: str,
    tema_slug: str,
    numero_providencia: str,
    html_bytes: bytes,
    metadata: dict,
) -> tuple[Path, Path]:
    """Guarda el HTML original (bytes tal cual) y el metadata.json. Devuelve
    (ruta_html, ruta_metadata) relativas a output_dir."""
    carpeta = carpeta_destino(output_dir, area_slug, tema_slug)
    carpeta.mkdir(parents=True, exist_ok=True)

    base = nombre_archivo_base(numero_providencia)
    ruta_html = carpeta / f"{base}.htm"
    ruta_metadata = carpeta / f"{base}_metadata.json"

    ruta_html.write_bytes(html_bytes)
    ruta_metadata.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    return ruta_html, ruta_metadata
