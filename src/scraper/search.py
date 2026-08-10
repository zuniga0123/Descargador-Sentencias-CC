"""Búsqueda de providencias en el buscador de la Relatoría (resultados en HTML)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from src import config
from src.scraper.client import RateLimitedClient

logger = logging.getLogger(__name__)


@dataclass
class ResultadoBusqueda:
    prov_id: str | None
    numero_providencia: str
    url_providencia: str
    fecha_sentencia: str | None
    fecha_publicacion: str | None
    tema: str | None
    resumen: str | None


def construir_url_busqueda(
    buscar_por: str,
    finicio: str,
    ffin: str,
    search_option: str = config.DEFAULT_SEARCH_OPTION,
    cant_providencias: int = config.DEFAULT_CANT_PROVIDENCIAS,
    order_by: str = config.DEFAULT_ORDER_BY,
) -> str:
    cant_providencias = min(cant_providencias, config.MAX_CANT_PROVIDENCIAS)
    params = {
        "searchOption": search_option,
        "buscar_por": buscar_por,
        "finicio": finicio,
        "ffin": ffin,
        "accion": "search",
        "ver_formulario": "si",
        "volver_a": "relatoria",
        "OrderbyOption": order_by,
        "cant_providencias": cant_providencias,
    }
    return f"{config.BUSCADOR_BASE}?{urlencode(params)}"


def _extraer_tema_resumen(celda) -> tuple[str | None, str | None]:
    """La celda 'Tema / Resumen' tiene el formato:
    <b>TEMA: </b>...texto...<br><b>RESUMEN: </b>...texto...
    """
    texto_completo = celda.get_text(separator="\n", strip=True)
    tema = None
    resumen = None
    if "TEMA:" in texto_completo:
        resto = texto_completo.split("TEMA:", 1)[1]
        if "RESUMEN:" in resto:
            tema_txt, resumen_txt = resto.split("RESUMEN:", 1)
            tema = tema_txt.strip()
            resumen = resumen_txt.strip()
        else:
            tema = resto.strip()
    return tema or None, resumen or None


def parsear_resultados(html: str) -> list[ResultadoBusqueda]:
    soup = BeautifulSoup(html, "html.parser")
    tabla = soup.find("table", id="tablet_results")
    if tabla is None:
        return []
    tbody = tabla.find("tbody")
    if tbody is None:
        return []

    resultados: list[ResultadoBusqueda] = []
    for fila in tbody.find_all("tr", recursive=False):
        celdas = fila.find_all("td", recursive=False)
        if len(celdas) < 4:
            continue

        celda_providencia = celdas[0]
        prov_input = celda_providencia.find("input", attrs={"type": "hidden"})
        prov_id = prov_input.get("value") if prov_input else None

        link = celda_providencia.find("a", title="Ver providencia")
        if link is None:
            continue
        numero_providencia = link.get_text(strip=True)
        url_providencia = link.get("href", "")

        fecha_sentencia = celdas[1].get_text(strip=True) or None
        tema, resumen = _extraer_tema_resumen(celdas[2])
        fecha_publicacion = celdas[3].get_text(strip=True) or None

        resultados.append(
            ResultadoBusqueda(
                prov_id=prov_id,
                numero_providencia=numero_providencia,
                url_providencia=url_providencia,
                fecha_sentencia=fecha_sentencia,
                fecha_publicacion=fecha_publicacion,
                tema=tema,
                resumen=resumen,
            )
        )
    return resultados


def buscar(
    client: RateLimitedClient,
    buscar_por: str,
    finicio: str,
    ffin: str,
    search_option: str = config.DEFAULT_SEARCH_OPTION,
    cant_providencias: int = config.DEFAULT_CANT_PROVIDENCIAS,
) -> list[ResultadoBusqueda]:
    url = construir_url_busqueda(
        buscar_por=buscar_por,
        finicio=finicio,
        ffin=ffin,
        search_option=search_option,
        cant_providencias=cant_providencias,
    )
    logger.info("Buscando: %s", url)
    response = client.get(url)
    resultados = parsear_resultados(response.text)
    logger.info("Se encontraron %d resultado(s)", len(resultados))
    return resultados


# Tipos de providencia oficiales del buscador (facetas del panel lateral,
# ver aggs_prov_tipo[] en la página de resultados). No incluye "Auto" a
# propósito: ese valor sí existe en el buscador pero se deja fuera de este
# mapa porque el caso de uso principal es traer solo sentencias.
TIPOS_PROVIDENCIA = {
    "T": "Tutela",
    "SU": "Sentencia de unificación",
    "C": "Constitucionalidad",
    "AUTO": "Auto",
}


def buscar_por_tipo_y_anio(
    client: RateLimitedClient,
    tipo: str,
    anio: int,
    finicio: str = "1992-01-01",
    ffin: str | None = None,
    search_option: str = "texto",
    cant_providencias: int = config.MAX_CANT_PROVIDENCIAS,
) -> list[ResultadoBusqueda]:
    """Busca providencias por tipo (ver TIPOS_PROVIDENCIA) y año de sentencia,
    usando los filtros ("facetas") del panel lateral del buscador.

    IMPORTANTE: el WAF del sitio bloquea (HTTP 500) cualquier solicitud que
    repita el mismo nombre de campo más de una vez en el POST (parameter
    pollution). Por eso esta función solo admite UN tipo y UN año a la vez;
    para combinar varios tipos/años hay que hacer una solicitud por cada
    combinación (ver pipeline.ejecutar_por_tipos_y_anios).
    """
    tipo_label = TIPOS_PROVIDENCIA.get(tipo.upper(), tipo)
    cant_providencias = min(cant_providencias, config.MAX_CANT_PROVIDENCIAS)
    data = {
        "searchOption": search_option,
        "buscar_por": "",
        "finicio": finicio,
        "ffin": ffin or f"{anio}-12-31",
        "ver_formulario": "si",
        "volver_a": "relatoria",
        "OrderbyOption": config.DEFAULT_ORDER_BY,
        "cant_providencias": cant_providencias,
        "maxprov": cant_providencias,
        "accion": "searchByAggs",
        "aggs_prov_tipo[]": f"prov_tipo|{tipo_label}|0",
        "aggs_prov_f_sentencia[]": f"prov_f_sentencia|{anio}|0",
    }
    logger.info("Buscando por facetas: tipo=%s año=%s", tipo_label, anio)
    response = client.post(config.BUSCADOR_INDEX, data=data)
    resultados = parsear_resultados(response.text)
    logger.info("tipo=%s año=%s -> %d resultado(s)", tipo_label, anio, len(resultados))
    return resultados
