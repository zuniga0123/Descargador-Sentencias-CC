"""Construcción de la URL de búsqueda y orquestación: intenta Excel primero, cae a HTML."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace

from . import config
from .excel_export import download_excel, parse_excel
from .http_client import RateLimitedClient
from .models import SearchResult
from .parsing import parse_resultados_table

logger = logging.getLogger(__name__)


@dataclass
class SearchParams:
    buscar_por: str
    finicio: str  # YYYY-MM-DD
    ffin: str  # YYYY-MM-DD
    search_option: str = config.SEARCH_OPTIONS["texto_providencia"]
    cant_providencias: int = config.CANT_PROVIDENCIAS_DEFAULT
    orderby: str = config.ORDERBY_DEFAULT

    def to_query_params(self) -> dict:
        return {
            "searchOption": self.search_option,
            "buscar_por": self.buscar_por,
            "finicio": self.finicio,
            "ffin": self.ffin,
            "accion": "search",
            "ver_formulario": "si",
            "volver_a": "relatoria",
            "OrderbyOption": self.orderby,
            "cant_providencias": min(self.cant_providencias, config.CANT_PROVIDENCIAS_MAX),
        }


def build_search_url(params: SearchParams) -> tuple[str, dict]:
    """Devuelve (url_base, query_params) listos para pasar a requests."""
    return config.BUSCADOR_URL, params.to_query_params()


def guess_ficha_url(radicado: str) -> str:
    """Reconstruye la URL de la ficha individual a partir del radicado cuando el listado no la trae.

    Formato observado: /relatoria/{anio}/{RADICADO}.htm, con el radicado
    terminando en año de 2 dígitos (ej. T-388-19 -> 2019). Asume el mismo
    rango de años del ejemplo del brief (1992-actualidad); providencias muy
    antiguas o con formato de radicado distinto pueden requerir ajuste manual.
    """
    sufijo = radicado.rsplit("-", 1)[-1]
    anio_2d = int(sufijo)
    anio = 1900 + anio_2d if anio_2d >= 92 else 2000 + anio_2d
    return f"{config.BASE_URL}/relatoria/{anio}/{radicado}.htm"


def run_search(client: RateLimitedClient, params: SearchParams) -> tuple[list[SearchResult], str]:
    """Ejecuta la búsqueda. Devuelve (resultados, metodo) con metodo en {'excel', 'html'}."""
    url, query = build_search_url(params)
    html = client.get_text(url, params=query)

    excel_bytes = download_excel(client, html, url)
    if excel_bytes:
        try:
            resultados = parse_excel(excel_bytes)
            if resultados:
                resultados = [
                    r if r.url_ficha else replace(r, url_ficha=guess_ficha_url(r.radicado))
                    for r in resultados
                ]
                return resultados, "excel"
            logger.warning("La exportación a Excel vino vacía, cayendo a parsing HTML.")
        except ValueError as exc:
            logger.warning("No se pudo parsear el Excel exportado (%s), cayendo a parsing HTML.", exc)

    resultados = parse_resultados_table(html, url)
    return resultados, "html"
