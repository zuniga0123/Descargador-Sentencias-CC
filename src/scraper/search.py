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
    soup = BeautifulSoup(html, "lxml")
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
