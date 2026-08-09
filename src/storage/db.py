"""Índice SQLite de providencias descargadas."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS providencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_providencia TEXT NOT NULL UNIQUE,
    corte TEXT NOT NULL DEFAULT 'corte-constitucional',
    radicado TEXT,
    tipo_proceso TEXT,
    fecha_sentencia TEXT,
    fecha_publicacion TEXT,
    magistrados_ponentes TEXT,
    area_slug TEXT NOT NULL,
    area_nombre TEXT NOT NULL,
    metodo_clasificacion TEXT,
    justificacion_clasificacion TEXT,
    tema_busqueda TEXT,
    resumen TEXT,
    temas_oficiales TEXT,
    subtemas_oficiales TEXT,
    prov_id TEXT,
    url_origen TEXT NOT NULL,
    ruta_html TEXT NOT NULL,
    ruta_metadata TEXT NOT NULL,
    fecha_descarga TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_providencias_area ON providencias(area_slug);
CREATE INDEX IF NOT EXISTS idx_providencias_fecha_publicacion ON providencias(fecha_publicacion);
"""

UPSERT_SQL = """
INSERT INTO providencias (
    numero_providencia, corte, radicado, tipo_proceso, fecha_sentencia, fecha_publicacion,
    magistrados_ponentes, area_slug, area_nombre, metodo_clasificacion, justificacion_clasificacion,
    tema_busqueda, resumen, temas_oficiales, subtemas_oficiales, prov_id, url_origen,
    ruta_html, ruta_metadata, fecha_descarga
) VALUES (
    :numero_providencia, :corte, :radicado, :tipo_proceso, :fecha_sentencia, :fecha_publicacion,
    :magistrados_ponentes, :area_slug, :area_nombre, :metodo_clasificacion, :justificacion_clasificacion,
    :tema_busqueda, :resumen, :temas_oficiales, :subtemas_oficiales, :prov_id, :url_origen,
    :ruta_html, :ruta_metadata, :fecha_descarga
)
ON CONFLICT(numero_providencia) DO UPDATE SET
    corte=excluded.corte,
    radicado=excluded.radicado,
    tipo_proceso=excluded.tipo_proceso,
    fecha_sentencia=excluded.fecha_sentencia,
    fecha_publicacion=excluded.fecha_publicacion,
    magistrados_ponentes=excluded.magistrados_ponentes,
    area_slug=excluded.area_slug,
    area_nombre=excluded.area_nombre,
    metodo_clasificacion=excluded.metodo_clasificacion,
    justificacion_clasificacion=excluded.justificacion_clasificacion,
    tema_busqueda=excluded.tema_busqueda,
    resumen=excluded.resumen,
    temas_oficiales=excluded.temas_oficiales,
    subtemas_oficiales=excluded.subtemas_oficiales,
    prov_id=excluded.prov_id,
    url_origen=excluded.url_origen,
    ruta_html=excluded.ruta_html,
    ruta_metadata=excluded.ruta_metadata,
    fecha_descarga=excluded.fecha_descarga
"""


def conectar(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def existe_providencia(conn: sqlite3.Connection, numero_providencia: str) -> bool:
    cursor = conn.execute(
        "SELECT 1 FROM providencias WHERE numero_providencia = ? LIMIT 1", (numero_providencia,)
    )
    return cursor.fetchone() is not None


def upsert_providencia(conn: sqlite3.Connection, registro: dict) -> None:
    conn.execute(UPSERT_SQL, registro)
    conn.commit()


def obtener_ultima_fecha_publicacion(conn: sqlite3.Connection) -> str | None:
    cursor = conn.execute(
        "SELECT MAX(fecha_publicacion) AS max_fecha FROM providencias WHERE fecha_publicacion IS NOT NULL"
    )
    fila = cursor.fetchone()
    return fila["max_fecha"] if fila else None


def contar_providencias(conn: sqlite3.Connection) -> int:
    cursor = conn.execute("SELECT COUNT(*) AS total FROM providencias")
    return cursor.fetchone()["total"]
