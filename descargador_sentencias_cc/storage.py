"""Índice SQLite y organización de carpetas corte -> área -> tema -> subtema."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from . import config
from .models import Providencia
from .utils import slugify

SCHEMA = """
CREATE TABLE IF NOT EXISTS providencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    radicado TEXT UNIQUE NOT NULL,
    tipo_providencia TEXT,
    fecha_sentencia TEXT,
    fecha_publicacion TEXT,
    sala TEXT,
    ponente TEXT,
    tema_oficial TEXT,
    subtema_oficial TEXT,
    resumen TEXT,
    area_slug TEXT,
    area_label TEXT,
    area_metodo TEXT,
    url_ficha TEXT,
    ruta_archivo TEXT,
    hash_contenido TEXT,
    fecha_descarga TEXT,
    creado_en TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_providencias_fecha_publicacion ON providencias (fecha_publicacion);
CREATE INDEX IF NOT EXISTS idx_providencias_area ON providencias (area_slug);
"""


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def providencia_existe(conn: sqlite3.Connection, radicado: str) -> bool:
    cur = conn.execute("SELECT 1 FROM providencias WHERE radicado = ?", (radicado,))
    return cur.fetchone() is not None


def get_ultima_fecha_publicacion(conn: sqlite3.Connection) -> str | None:
    cur = conn.execute("SELECT MAX(fecha_publicacion) AS m FROM providencias")
    row = cur.fetchone()
    return row["m"] if row and row["m"] else None


def upsert_providencia(conn: sqlite3.Connection, providencia: Providencia) -> None:
    r = providencia.resultado
    conn.execute(
        """
        INSERT INTO providencias (
            radicado, tipo_providencia, fecha_sentencia, fecha_publicacion, sala, ponente,
            tema_oficial, subtema_oficial, resumen, area_slug, area_label, area_metodo,
            url_ficha, ruta_archivo, hash_contenido, fecha_descarga
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(radicado) DO UPDATE SET
            tipo_providencia=excluded.tipo_providencia,
            fecha_sentencia=excluded.fecha_sentencia,
            fecha_publicacion=excluded.fecha_publicacion,
            sala=excluded.sala,
            ponente=excluded.ponente,
            tema_oficial=excluded.tema_oficial,
            subtema_oficial=excluded.subtema_oficial,
            resumen=excluded.resumen,
            area_slug=excluded.area_slug,
            area_label=excluded.area_label,
            area_metodo=excluded.area_metodo,
            url_ficha=excluded.url_ficha,
            ruta_archivo=excluded.ruta_archivo,
            hash_contenido=excluded.hash_contenido,
            fecha_descarga=excluded.fecha_descarga
        """,
        (
            r.radicado,
            r.tipo_providencia,
            r.fecha_sentencia,
            r.fecha_publicacion,
            r.sala,
            r.ponente,
            r.tema_oficial,
            r.subtema_oficial,
            r.resumen,
            providencia.area_slug,
            providencia.area_label,
            providencia.area_metodo,
            r.url_ficha,
            providencia.ruta_archivo,
            providencia.hash_contenido,
            providencia.fecha_descarga,
        ),
    )
    conn.commit()


def build_output_dir(
    out_dir: str | Path,
    area_slug: str,
    tema_oficial: str | None,
    subtema_oficial: str | None,
) -> Path:
    """corte-constitucional/area/tema/[subtema]/, creando las carpetas si no existen."""
    partes = [out_dir, config.CORTE_SLUG, area_slug, slugify(tema_oficial, default="sin-tema")]
    if subtema_oficial:
        partes.append(slugify(subtema_oficial, default="sin-subtema"))
    path = Path(*[str(p) for p in partes])
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_providencia_files(dir_path: Path, radicado: str, html: str, metadata: dict) -> Path:
    """Guarda RADICADO.htm y RADICADO_metadata.json en dir_path. Devuelve la ruta del .htm."""
    ruta_html = dir_path / f"{radicado}.htm"
    ruta_json = dir_path / f"{radicado}_metadata.json"
    ruta_html.write_text(html, encoding="utf-8")
    ruta_json.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta_html
