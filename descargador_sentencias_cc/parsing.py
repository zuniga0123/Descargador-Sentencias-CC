"""Parsing de HTML del buscador de Relatoría.

IMPORTANTE: al momento de escribir este módulo no fue posible acceder al
sitio real (bloqueo de red del entorno de desarrollo), por lo que estas
heurísticas están basadas en la descripción del brief, no en el marcado
HTML real capturado. Están escritas para ser tolerantes a variaciones
(regex sobre el href del link de la providencia, extracción de campos por
etiqueta de texto en vez de selectores CSS frágiles), pero DEBEN calibrarse
contra el sitio real antes de confiar en los resultados en producción. Usa
el subcomando `inspeccionar-formulario` / `inspeccionar-resultados` de la
CLI para volcar la estructura real y ajustar aquí lo que haga falta.
"""

from __future__ import annotations

import re
from dataclasses import replace
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .models import SearchResult

# Coincide con hrefs del estilo /relatoria/2019/T-388-19.htm
RADICADO_LINK_RE = re.compile(
    r"/relatoria/(?P<anio>\d{4})/(?P<radicado>[A-Za-z]{1,4}-\d+-\d+)\.html?",
    re.IGNORECASE,
)

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b")


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def find_ficha_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """Devuelve pares (radicado, url_absoluta) de todos los links a fichas individuales."""
    soup = BeautifulSoup(html, "lxml")
    vistos: set[str] = set()
    resultado: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=RADICADO_LINK_RE):
        href = a["href"]
        match = RADICADO_LINK_RE.search(href)
        if not match:
            continue
        radicado = match.group("radicado").upper()
        if radicado in vistos:
            continue
        vistos.add(radicado)
        resultado.append((radicado, urljoin(base_url, href)))
    return resultado


def _extract_labeled(text: str, labels: list[str], stop_labels: list[str]) -> str | None:
    """Busca la primera etiqueta (ej. 'TEMA:') y captura el texto hasta la siguiente etiqueta de parada."""
    label_pattern = "|".join(re.escape(l) for l in labels)
    stop_pattern = "|".join(re.escape(l) for l in stop_labels) if stop_labels else None

    match = re.search(rf"(?:{label_pattern})\s*:?\s*", text, re.IGNORECASE)
    if not match:
        return None
    start = match.end()
    if stop_pattern:
        stop_match = re.search(stop_pattern, text[start:], re.IGNORECASE)
        end = start + stop_match.start() if stop_match else len(text)
    else:
        end = len(text)
    return _normalize_ws(text[start:end]) or None


def parse_resultados_table(html: str, base_url: str) -> list[SearchResult]:
    """Extrae SearchResult de la página de resultados en HTML (fallback si no hay export a Excel)."""
    soup = BeautifulSoup(html, "lxml")
    anchors = soup.find_all("a", href=RADICADO_LINK_RE)

    resultados: list[SearchResult] = []
    vistos: set[str] = set()

    for a in anchors:
        match = RADICADO_LINK_RE.search(a["href"])
        if not match:
            continue
        radicado = match.group("radicado").upper()
        if radicado in vistos:
            continue
        vistos.add(radicado)

        # Contenedor de la fila: preferimos <tr>, si no existe subimos hasta
        # encontrar un bloque razonable (div/li) con más de un poco de texto.
        contenedor = a.find_parent("tr")
        if contenedor is None:
            contenedor = a.find_parent(["li", "div"])
        if contenedor is None:
            contenedor = a.parent

        texto = _normalize_ws(contenedor.get_text(" "))

        fechas = DATE_RE.findall(texto)
        fecha_sentencia = fechas[0] if len(fechas) >= 1 else None
        fecha_publicacion = fechas[1] if len(fechas) >= 2 else None

        tema = _extract_labeled(texto, ["TEMA"], ["RESUMEN", "FECHA"])
        resumen = _extract_labeled(texto, ["RESUMEN"], ["FECHA"])

        resultados.append(
            SearchResult(
                radicado=radicado,
                url_ficha=urljoin(base_url, a["href"]),
                fecha_sentencia=fecha_sentencia,
                fecha_publicacion=fecha_publicacion,
                tema_oficial=tema,
                resumen=resumen or (texto if not tema and not resumen else None),
            )
        )

    return resultados


TEMA_SUBTEMA_RE = re.compile(r"^(?P<tema>[A-ZÁÉÍÓÚÑ0-9 ,.()/'\"]+?)\s*-\s*(?P<subtema>.+)$")


def split_tema_subtema(raw: str) -> tuple[str, str | None]:
    """Divide 'TEMA EN MAYUSCULAS-Subtema' en (tema, subtema). Si no calza el patrón, todo es tema."""
    raw = _normalize_ws(raw)
    match = TEMA_SUBTEMA_RE.match(raw)
    if match:
        return match.group("tema").strip(), match.group("subtema").strip()
    return raw, None


def extract_tema_subtema_ficha(html: str) -> list[tuple[str, str | None]]:
    """Extrae los pares (tema, subtema) oficiales de la ficha individual de una providencia.

    La Relatoría puede listar varios temas/subtemas por providencia, separados
    por salto de línea o punto y coma en el bloque de la ficha.
    """
    soup = BeautifulSoup(html, "lxml")
    texto = soup.get_text("\n")

    bloque = _extract_labeled(
        texto,
        labels=["Temas", "Tema", "TEMA"],
        stop_labels=["Palabras clave", "Norma", "Salvamento", "Aclaración de voto"],
    )
    if not bloque:
        return []

    items = re.split(r"[\n;]+", bloque)
    pares = []
    for item in items:
        item = item.strip(" .-")
        if not item:
            continue
        pares.append(split_tema_subtema(item))
    return pares


def find_export_excel_link(html: str, base_url: str) -> str | None:
    """Busca el link/botón 'Exportar resultados en EXCEL' en la página de resultados."""
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        texto = _normalize_ws(a.get_text(" ")).lower()
        href = a["href"].lower()
        if "excel" in texto or "excel" in href or ".xls" in href:
            return urljoin(base_url, a["href"])
    return None


def enrich_with_ficha(resultado: SearchResult, ficha_html: str) -> SearchResult:
    """Completa tema/subtema oficial de un SearchResult usando la ficha individual, si no venían del listado."""
    if resultado.tema_oficial and resultado.subtema_oficial:
        return resultado
    pares = extract_tema_subtema_ficha(ficha_html)
    if not pares:
        return resultado
    tema, subtema = pares[0]
    return replace(
        resultado,
        tema_oficial=resultado.tema_oficial or tema,
        subtema_oficial=resultado.subtema_oficial or subtema,
    )
