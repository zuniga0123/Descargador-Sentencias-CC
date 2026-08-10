"""Orquesta el flujo completo: buscar -> ficha -> titulaciones -> clasificar -> guardar -> indexar."""

from __future__ import annotations

import datetime as dt
import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from src import config
from src.classify.classify import clasificar
from src.scraper import detail, download, search, titulaciones as titulaciones_mod
from src.scraper.client import RateLimitedClient
from src.storage import db, files

logger = logging.getLogger(__name__)

FECHA_INICIO_POR_DEFECTO = "1992-01-01"


@dataclass
class ResumenEjecucion:
    encontradas: int = 0
    nuevas: int = 0
    actualizadas: int = 0
    saltadas: int = 0
    errores: int = 0
    detalles_error: list[str] = field(default_factory=list)


def _fecha_hoy() -> str:
    return dt.date.today().isoformat()


def _procesar_resultado(
    client: RateLimitedClient,
    conn: sqlite3.Connection,
    resultado: search.ResultadoBusqueda,
    output_dir: Path,
    usar_ia: bool,
    dry_run: bool,
    forzar_reprocesar: bool,
    resumen: ResumenEjecucion,
) -> None:
    """Procesa un único resultado de búsqueda (ficha, titulaciones, clasificación,
    guardado y registro en el índice) y actualiza `resumen` in-place."""
    numero = resultado.numero_providencia
    try:
        if not forzar_reprocesar and db.existe_providencia(conn, numero):
            logger.info("Ya existe en el índice, se omite: %s", numero)
            resumen.saltadas += 1
            return

        es_nueva = not db.existe_providencia(conn, numero)

        detalle = detail.obtener_detalle(client, numero)
        prov_id = resultado.prov_id or (detalle.prov_id if detalle else None)

        titus = titulaciones_mod.obtener_titulaciones(client, prov_id) if prov_id else []
        temas_oficiales = list(dict.fromkeys(t.tema for t in titus))
        subtemas_oficiales = list(dict.fromkeys(t.subtema for t in titus if t.subtema))

        resultado_clasificacion = clasificar(
            temas_oficiales=temas_oficiales,
            tema_busqueda=resultado.tema,
            resumen=resultado.resumen,
            numero_providencia=numero,
            usar_ia=usar_ia,
        )

        tema_para_carpeta = temas_oficiales[0] if temas_oficiales else (resultado.tema or "sin-tema")
        tema_slug = files.slugificar(tema_para_carpeta)

        if dry_run:
            logger.info(
                "[dry-run] %s -> área=%s tema_carpeta=%s (método=%s)",
                numero,
                resultado_clasificacion.area.slug,
                tema_slug,
                resultado_clasificacion.metodo,
            )
            if es_nueva:
                resumen.nuevas += 1
            else:
                resumen.actualizadas += 1
            return

        html_bytes = download.descargar_html_providencia(client, resultado.url_providencia)

        metadata = {
            "numero_providencia": numero,
            "corte": config.CORTE_SLUG,
            "radicado": detalle.numero_expediente if detalle else None,
            "tipo_proceso": detalle.tipo_proceso if detalle else None,
            "fecha_sentencia": resultado.fecha_sentencia or (detalle.fecha_fallo if detalle else None),
            "fecha_publicacion": resultado.fecha_publicacion or (detalle.fecha_publicacion if detalle else None),
            "magistrados_ponentes": detalle.magistrados_ponentes if detalle else [],
            "salvamentos_aclaraciones": detalle.salvamentos_aclaraciones if detalle else [],
            "instancias": detalle.instancias if detalle else [],
            "area": {
                "slug": resultado_clasificacion.area.slug,
                "nombre": resultado_clasificacion.area.nombre,
            },
            "metodo_clasificacion": resultado_clasificacion.metodo,
            "justificacion_clasificacion": resultado_clasificacion.justificacion,
            "tema_busqueda": resultado.tema,
            "resumen": resultado.resumen,
            "temas_subtemas_oficiales": [
                {"tema": t.tema, "subtema": t.subtema} for t in titus
            ],
            "texto_resuelve": detalle.texto_resuelve if detalle else None,
            "prov_id": prov_id,
            "url_origen": resultado.url_providencia,
            "fecha_descarga": dt.datetime.now(dt.timezone.utc).isoformat(),
            "campos_adicionales_ficha": detalle.campos_adicionales if detalle else {},
        }

        ruta_html, ruta_metadata = files.guardar_providencia(
            output_dir=output_dir,
            area_slug=resultado_clasificacion.area.slug,
            tema_slug=tema_slug,
            numero_providencia=numero,
            html_bytes=html_bytes,
            metadata=metadata,
        )

        registro = {
            "numero_providencia": numero,
            "corte": config.CORTE_SLUG,
            "radicado": metadata["radicado"],
            "tipo_proceso": metadata["tipo_proceso"],
            "fecha_sentencia": metadata["fecha_sentencia"],
            "fecha_publicacion": metadata["fecha_publicacion"],
            "magistrados_ponentes": "; ".join(metadata["magistrados_ponentes"]),
            "area_slug": resultado_clasificacion.area.slug,
            "area_nombre": resultado_clasificacion.area.nombre,
            "metodo_clasificacion": resultado_clasificacion.metodo,
            "justificacion_clasificacion": resultado_clasificacion.justificacion,
            "tema_busqueda": resultado.tema,
            "resumen": resultado.resumen,
            "temas_oficiales": "; ".join(temas_oficiales),
            "subtemas_oficiales": "; ".join(subtemas_oficiales),
            "prov_id": prov_id,
            "url_origen": resultado.url_providencia,
            "ruta_html": str(ruta_html),
            "ruta_metadata": str(ruta_metadata),
            "fecha_descarga": metadata["fecha_descarga"],
        }
        db.upsert_providencia(conn, registro)

        if es_nueva:
            resumen.nuevas += 1
            logger.info("Descargada: %s -> %s", numero, resultado_clasificacion.area.slug)
        else:
            resumen.actualizadas += 1
            logger.info("Actualizada: %s -> %s", numero, resultado_clasificacion.area.slug)

    except Exception as exc:  # noqa: BLE001 - se registra y se continúa con el resto
        logger.exception("Error procesando %s", numero)
        resumen.errores += 1
        resumen.detalles_error.append(f"{numero}: {exc}")


def ejecutar(
    buscar_por: str,
    finicio: str | None = None,
    ffin: str | None = None,
    search_option: str = config.DEFAULT_SEARCH_OPTION,
    cant_providencias: int = config.DEFAULT_CANT_PROVIDENCIAS,
    output_dir: Path = config.DEFAULT_OUTPUT_DIR,
    db_path: Path = config.DEFAULT_DB_PATH,
    incremental: bool = False,
    usar_ia: bool = True,
    max_resultados: int | None = None,
    rate_limit_seconds: float = config.DEFAULT_RATE_LIMIT_SECONDS,
    dry_run: bool = False,
    forzar_reprocesar: bool = False,
) -> ResumenEjecucion:
    conn = db.conectar(db_path)
    resumen = ResumenEjecucion()

    if incremental:
        ultima_fecha = db.obtener_ultima_fecha_publicacion(conn)
        finicio = ultima_fecha or finicio or FECHA_INICIO_POR_DEFECTO
        ffin = ffin or _fecha_hoy()
        logger.info("Modo incremental: finicio=%s ffin=%s (última fecha registrada=%s)", finicio, ffin, ultima_fecha)
    else:
        finicio = finicio or FECHA_INICIO_POR_DEFECTO
        ffin = ffin or _fecha_hoy()

    client = RateLimitedClient(rate_limit_seconds=rate_limit_seconds)

    resultados = search.buscar(
        client,
        buscar_por=buscar_por,
        finicio=finicio,
        ffin=ffin,
        search_option=search_option,
        cant_providencias=cant_providencias,
    )
    resumen.encontradas = len(resultados)

    if max_resultados is not None:
        resultados = resultados[:max_resultados]

    for resultado in resultados:
        _procesar_resultado(client, conn, resultado, output_dir, usar_ia, dry_run, forzar_reprocesar, resumen)

    conn.close()
    return resumen


def ejecutar_por_tipos_y_anios(
    tipos: list[str],
    anios: list[int],
    output_dir: Path = config.DEFAULT_OUTPUT_DIR,
    db_path: Path = config.DEFAULT_DB_PATH,
    usar_ia: bool = True,
    max_resultados: int | None = None,
    rate_limit_seconds: float = config.DEFAULT_RATE_LIMIT_SECONDS,
    dry_run: bool = False,
    forzar_reprocesar: bool = False,
) -> ResumenEjecucion:
    """Descarga todas las providencias de los tipos y años indicados (ej. Tutela,
    Constitucionalidad y Sentencia de Unificación de los últimos 7 años), usando
    los filtros ("facetas") del buscador. Se hace una solicitud por cada
    combinación tipo+año porque el WAF del sitio bloquea solicitudes que repiten
    el mismo campo de filtro (ver search.buscar_por_tipo_y_anio)."""
    conn = db.conectar(db_path)
    resumen = ResumenEjecucion()
    client = RateLimitedClient(rate_limit_seconds=rate_limit_seconds)

    total_procesados = 0
    for tipo in tipos:
        for anio in anios:
            if max_resultados is not None and total_procesados >= max_resultados:
                break
            resultados = search.buscar_por_tipo_y_anio(client, tipo=tipo, anio=anio)
            resumen.encontradas += len(resultados)

            for resultado in resultados:
                if max_resultados is not None and total_procesados >= max_resultados:
                    break
                _procesar_resultado(client, conn, resultado, output_dir, usar_ia, dry_run, forzar_reprocesar, resumen)
                total_procesados += 1

    conn.close()
    return resumen
