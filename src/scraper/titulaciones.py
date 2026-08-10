"""Temas/subtemas oficiales (taxonomía de la Relatoría) para una providencia.

Endpoint descubierto en assets/js/buscadorV1.js (función f_visualizar_titulaciones):
POST {BUSCADOR_INDEX} con accion=ver_titulacionesXIDprovidencia y prov_id=<id interno>.
Devuelve una tabla de pares Tema(descriptor) / Subtema(restrictor); una providencia
puede tener varias filas (varios temas y/o varios subtemas por tema).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from bs4 import BeautifulSoup

from src import config
from src.scraper.client import RateLimitedClient

logger = logging.getLogger(__name__)


@dataclass
class Titulacion:
    tema: str
    subtema: str | None


def parsear_titulaciones(html: str) -> list[Titulacion]:
    soup = BeautifulSoup(html, "html.parser")
    tabla = soup.find("table", id="tablet_titulaciones")
    if tabla is None:
        return []
    tbody = tabla.find("tbody")
    if tbody is None:
        return []

    titulaciones: list[Titulacion] = []
    for fila in tbody.find_all("tr", recursive=False):
        celdas = fila.find_all("td", recursive=False)
        if len(celdas) < 2:
            continue
        tema = celdas[0].get_text(strip=True)
        subtema = celdas[1].get_text(strip=True) or None
        if tema:
            titulaciones.append(Titulacion(tema=tema, subtema=subtema))
    return titulaciones


def obtener_titulaciones(client: RateLimitedClient, prov_id: str) -> list[Titulacion]:
    data = {
        "prov_id": prov_id,
        "accion": "ver_titulacionesXIDprovidencia",
    }
    response = client.post(config.BUSCADOR_INDEX, data=data)
    titulaciones = parsear_titulaciones(response.text)
    logger.debug("prov_id=%s -> %d titulación(es)", prov_id, len(titulaciones))
    return titulaciones
