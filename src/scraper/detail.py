"""Ficha/detalle de una providencia: expediente, fechas, magistrados, resuelve.

Endpoint descubierto en assets/js/buscadorV1.js (función f_modal_ProvidenciaXNumSentencia):
POST {BUSCADOR_INDEX} con accion=ver_modal_detalle_providencia y prov_sentencia=<numero>.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from src import config
from src.scraper.client import RateLimitedClient

logger = logging.getLogger(__name__)

_RE_SOLO_DIGITOS = re.compile(r"^\d+$")


@dataclass
class DetalleProvidencia:
    prov_id: str | None
    numero_expediente: str | None
    tipo_proceso: str | None
    fecha_fallo: str | None
    fecha_publicacion: str | None
    magistrados_ponentes: list[str] = field(default_factory=list)
    salvamentos_aclaraciones: list[str] = field(default_factory=list)
    instancias: list[str] = field(default_factory=list)
    texto_resuelve: str | None = None
    campos_adicionales: dict[str, str | list[str]] = field(default_factory=dict)


def _normalizar_etiqueta(texto: str) -> str:
    return texto.strip().rstrip(":").strip().lower()


def _valor_de_columna(col_md_9) -> str | list[str]:
    lista = col_md_9.find("ul")
    if lista is not None:
        return [li.get_text(strip=True) for li in lista.find_all("li")]
    return col_md_9.get_text(strip=True)


def _parsear_campos_panel(panel_body) -> dict[str, str | list[str]]:
    campos: dict[str, str | list[str]] = {}
    for fila in panel_body.find_all("div", class_="row", recursive=False):
        columnas = fila.find_all("div", recursive=False)
        if len(columnas) < 2:
            continue
        etiqueta = _normalizar_etiqueta(columnas[0].get_text(strip=True))
        if not etiqueta:
            continue
        campos[etiqueta] = _valor_de_columna(columnas[1])
    return campos


def _extraer_numero_y_tipo(valor_numero: str | None) -> tuple[str | None, str | None]:
    if not valor_numero:
        return None, None
    match = re.match(r"^(.*?)\(([^)]*)\)\s*$", valor_numero.strip())
    if match:
        return match.group(1).strip(" -") or None, match.group(2).strip() or None
    return valor_numero.strip() or None, None


def _extraer_prov_id(soup: BeautifulSoup) -> str | None:
    for parrafo in soup.find_all("p", class_="text_gray_italic"):
        texto = parrafo.get_text(strip=True)
        if _RE_SOLO_DIGITOS.match(texto):
            return texto
    return None


def parsear_detalle(html: str) -> DetalleProvidencia | None:
    soup = BeautifulSoup(html, "html.parser")
    div_detalle = soup.find("div", id="div_detalle")
    if div_detalle is None:
        return None

    campos: dict[str, str | list[str]] = {}
    for panel_body in div_detalle.find_all("div", class_="panel-body"):
        campos.update(_parsear_campos_panel(panel_body))

    numero_expediente, tipo_proceso = _extraer_numero_y_tipo(campos.pop("número", None))

    ponentes = campos.pop("ponentes", [])
    if isinstance(ponentes, str):
        ponentes = [ponentes]
    salvamentos = campos.pop("salvamentosy/oaclaraciones", [])
    if isinstance(salvamentos, str):
        salvamentos = [salvamentos]
    instancias = campos.pop("instancias", [])
    if isinstance(instancias, str):
        instancias = [instancias]

    fecha_fallo = campos.pop("fallo", None)
    fecha_publicacion = campos.pop("publicación", None)

    resuelve_div = soup.find("div", id="collapsTextResuelve")
    texto_resuelve = None
    if resuelve_div is not None:
        texto_resuelve = resuelve_div.get_text(separator="\n", strip=True) or None

    return DetalleProvidencia(
        prov_id=_extraer_prov_id(soup),
        numero_expediente=numero_expediente,
        tipo_proceso=tipo_proceso,
        fecha_fallo=fecha_fallo if isinstance(fecha_fallo, str) else None,
        fecha_publicacion=fecha_publicacion if isinstance(fecha_publicacion, str) else None,
        magistrados_ponentes=ponentes,
        salvamentos_aclaraciones=salvamentos,
        instancias=instancias,
        texto_resuelve=texto_resuelve,
        campos_adicionales=campos,
    )


def obtener_detalle(client: RateLimitedClient, numero_providencia: str) -> DetalleProvidencia | None:
    data = {
        "prov_sentencia": numero_providencia,
        "accion": "ver_modal_detalle_providencia",
    }
    response = client.post(config.BUSCADOR_INDEX, data=data)
    detalle = parsear_detalle(response.text)
    if detalle is None:
        logger.warning("No se pudo parsear el detalle de %s", numero_providencia)
    return detalle
