"""Orquesta el flujo completo: buscar -> descargar ficha -> clasificar -> guardar."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import replace
from datetime import datetime, timezone

from . import search, storage, taxonomy
from .ai_classifier import AIClassifierError, classify_area_ai
from .http_client import RateLimitedClient
from .models import Providencia
from .parsing import enrich_with_ficha
from .search import SearchParams
from .taxonomy import AREAS, SIN_CLASIFICAR
from .utils import slugify

logger = logging.getLogger(__name__)


def run_pipeline(
    params: SearchParams,
    out_dir: str,
    db_path: str,
    use_ai: bool = True,
    incremental: bool = False,
    force: bool = False,
    rate_limit_seconds: float | None = None,
) -> dict:
    conn = storage.get_connection(db_path)
    storage.init_db(conn)

    if incremental:
        ultima = storage.get_ultima_fecha_publicacion(conn)
        if ultima and ultima > params.finicio:
            logger.info("Modo incremental: ajustando fecha inicial a %s (última publicación conocida).", ultima)
            params = replace(params, finicio=ultima)

    stats = {
        "encontrados": 0,
        "descargados": 0,
        "omitidos": 0,
        "errores": 0,
        "clasificados_regla": 0,
        "clasificados_ia": 0,
        "sin_clasificar": 0,
    }

    client_kwargs = {}
    if rate_limit_seconds is not None:
        client_kwargs["rate_limit_seconds"] = rate_limit_seconds

    with RateLimitedClient(**client_kwargs) as client:
        resultados, metodo = search.run_search(client, params)
        stats["encontrados"] = len(resultados)
        logger.info("Encontrados %d resultados (método: %s).", len(resultados), metodo)

        for resultado in resultados:
            if not force and storage.providencia_existe(conn, resultado.radicado):
                stats["omitidos"] += 1
                continue

            try:
                ficha_html = client.get_text(resultado.url_ficha)
            except Exception as exc:  # noqa: BLE001 - un error en una providencia no debe abortar el lote
                logger.error("Error descargando %s (%s): %s", resultado.radicado, resultado.url_ficha, exc)
                stats["errores"] += 1
                continue

            resultado = enrich_with_ficha(resultado, ficha_html)

            area_slug = taxonomy.classify_area_by_rules(
                resultado.tema_oficial, resultado.subtema_oficial, resultado.resumen
            )
            if area_slug:
                area_metodo = "regla"
                stats["clasificados_regla"] += 1
            elif use_ai:
                try:
                    area_slug, _justificacion = classify_area_ai(
                        resultado.tema_oficial, resultado.subtema_oficial, resultado.resumen
                    )
                    area_metodo = "ia"
                    stats["clasificados_ia"] += 1
                except AIClassifierError as exc:
                    logger.warning("Clasificación IA falló para %s: %s", resultado.radicado, exc)
                    area_slug = SIN_CLASIFICAR
                    area_metodo = "sin_clasificar"
                    stats["sin_clasificar"] += 1
            else:
                area_slug = SIN_CLASIFICAR
                area_metodo = "sin_clasificar"
                stats["sin_clasificar"] += 1

            area_label = AREAS[area_slug]
            hash_contenido = hashlib.sha256(ficha_html.encode("utf-8")).hexdigest()
            fecha_descarga = datetime.now(timezone.utc).isoformat()

            dir_path = storage.build_output_dir(
                out_dir, area_slug, resultado.tema_oficial, resultado.subtema_oficial
            )
            metadata = {
                "radicado": resultado.radicado,
                "tipo_providencia": resultado.tipo_providencia,
                "fecha_sentencia": resultado.fecha_sentencia,
                "fecha_publicacion": resultado.fecha_publicacion,
                "sala": resultado.sala,
                "ponente": resultado.ponente,
                "tema_oficial": resultado.tema_oficial,
                "subtema_oficial": resultado.subtema_oficial,
                "resumen": resultado.resumen,
                "area_slug": area_slug,
                "area_label": area_label,
                "area_metodo": area_metodo,
                "url_ficha": resultado.url_ficha,
                "hash_contenido": hash_contenido,
                "fecha_descarga": fecha_descarga,
            }
            ruta_html = storage.save_providencia_files(dir_path, resultado.radicado, ficha_html, metadata)

            providencia = Providencia(
                resultado=resultado,
                contenido_html=ficha_html,
                hash_contenido=hash_contenido,
                area_slug=area_slug,
                area_label=area_label,
                area_metodo=area_metodo,
                tema_slug=slugify(resultado.tema_oficial, default="sin-tema"),
                subtema_slug=slugify(resultado.subtema_oficial) if resultado.subtema_oficial else None,
                ruta_archivo=str(ruta_html),
                fecha_descarga=fecha_descarga,
            )
            storage.upsert_providencia(conn, providencia)
            stats["descargados"] += 1

    conn.close()
    return stats
