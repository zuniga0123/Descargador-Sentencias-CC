"""Convierte las providencias descargadas (HTML + metadata.json) a Markdown o
texto plano, listos para subir a SharePoint/OneDrive como base de conocimiento
de un agente de Microsoft 365 Copilot.

No hace ninguna solicitud de red: trabaja solo con lo que ya descargó
src.pipeline en la carpeta `jurisprudencia/`. Se eligió Markdown/texto plano
en vez de PDF para evitar depender de una librería de generación de PDF con
fuentes Unicode (riesgo de fallos de instalación/codificación en Windows,
como ya ocurrió con lxml); ambos formatos son indexados por SharePoint/Copilot
como texto completo.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

from src.scraper.download import decodificar_para_lectura

logger = logging.getLogger(__name__)

_RE_LINEAS_EN_BLANCO = re.compile(r"\n{3,}")
_RE_ESPACIOS_FINALES = re.compile(r"[ \t]+\n")


def extraer_texto_plano(html_bytes: bytes) -> str:
    """Extrae el texto legible del HTML original de la providencia (descarta
    estilos/metadatos de Word), conservando párrafos separados por líneas en
    blanco."""
    html = decodificar_para_lectura(html_bytes)
    soup = BeautifulSoup(html, "html.parser")

    cuerpo = soup.find("body") or soup
    texto = cuerpo.get_text(separator="\n")

    texto = _RE_ESPACIOS_FINALES.sub("\n", texto)
    lineas = [linea.strip() for linea in texto.split("\n")]
    texto = "\n".join(lineas)
    texto = _RE_LINEAS_EN_BLANCO.sub("\n\n", texto)
    return texto.strip()


def _lista_o_ninguno(valores: list[str] | None) -> str:
    if not valores:
        return "(no disponible)"
    return "\n".join(f"- {v}" for v in valores)


def construir_markdown(metadata: dict, texto_plano: str) -> str:
    numero = metadata.get("numero_providencia", "SIN-NUMERO")
    area = metadata.get("area", {}) or {}
    temas = metadata.get("temas_subtemas_oficiales") or []
    temas_fmt = [
        f"{t.get('tema', '')}" + (f" — {t['subtema']}" if t.get("subtema") else "")
        for t in temas
    ]

    partes = [
        f"# {numero}",
        "",
        f"**Corte:** {metadata.get('corte', 'corte-constitucional')}  ",
        f"**Radicado:** {metadata.get('radicado') or '(no disponible)'}  ",
        f"**Tipo de proceso:** {metadata.get('tipo_proceso') or '(no disponible)'}  ",
        f"**Fecha de sentencia:** {metadata.get('fecha_sentencia') or '(no disponible)'}  ",
        f"**Fecha de publicación:** {metadata.get('fecha_publicacion') or '(no disponible)'}  ",
        f"**Magistrado(s) ponente(s):** {', '.join(metadata.get('magistrados_ponentes') or []) or '(no disponible)'}  ",
        f"**Salvamentos/Aclaraciones:** {', '.join(metadata.get('salvamentos_aclaraciones') or []) or '(ninguno registrado)'}  ",
        f"**Área (clasificación propuesta):** {area.get('nombre') or '(sin clasificar)'}  ",
        f"**Método de clasificación:** {metadata.get('metodo_clasificacion') or '(no disponible)'}  ",
        "",
        "## Temas y subtemas oficiales (Relatoría)",
        "",
        _lista_o_ninguno(temas_fmt),
        "",
        "## Tema (encabezado del buscador)",
        "",
        metadata.get("tema_busqueda") or "(no disponible)",
        "",
        "## Resumen (síntesis de la Relatoría)",
        "",
        metadata.get("resumen") or "(no disponible)",
        "",
        "## Fuente",
        "",
        f"- URL original: {metadata.get('url_origen') or '(no disponible)'}",
        f"- Fecha de descarga: {metadata.get('fecha_descarga') or '(no disponible)'}",
        "",
        "---",
        "",
        "## Texto completo de la providencia",
        "",
        texto_plano,
        "",
    ]
    return "\n".join(partes)


def construir_texto_plano_documento(metadata: dict, texto_plano: str) -> str:
    numero = metadata.get("numero_providencia", "SIN-NUMERO")
    area = metadata.get("area", {}) or {}
    temas = metadata.get("temas_subtemas_oficiales") or []
    temas_fmt = [
        f"  - {t.get('tema', '')}" + (f" — {t['subtema']}" if t.get("subtema") else "")
        for t in temas
    ]

    partes = [
        f"PROVIDENCIA: {numero}",
        f"Radicado: {metadata.get('radicado') or '(no disponible)'}",
        f"Tipo de proceso: {metadata.get('tipo_proceso') or '(no disponible)'}",
        f"Fecha de sentencia: {metadata.get('fecha_sentencia') or '(no disponible)'}",
        f"Fecha de publicación: {metadata.get('fecha_publicacion') or '(no disponible)'}",
        f"Magistrado(s) ponente(s): {', '.join(metadata.get('magistrados_ponentes') or []) or '(no disponible)'}",
        f"Área (clasificación propuesta): {area.get('nombre') or '(sin clasificar)'}",
        "",
        "Temas y subtemas oficiales (Relatoría):",
        *(temas_fmt or ["  (no disponible)"]),
        "",
        f"Tema (encabezado del buscador): {metadata.get('tema_busqueda') or '(no disponible)'}",
        "",
        "Resumen (síntesis de la Relatoría):",
        metadata.get("resumen") or "(no disponible)",
        "",
        f"URL original: {metadata.get('url_origen') or '(no disponible)'}",
        "",
        "=" * 20 + " TEXTO COMPLETO DE LA PROVIDENCIA " + "=" * 20,
        "",
        texto_plano,
        "",
    ]
    return "\n".join(partes)


@dataclass
class ResumenExportacion:
    convertidos: int = 0
    errores: int = 0
    detalles_error: list[str] = field(default_factory=list)


def exportar_carpeta(
    input_dir: Path,
    output_dir: Path,
    formato: str = "md",
) -> ResumenExportacion:
    """Recorre `input_dir` (la carpeta `jurisprudencia/` generada por el
    pipeline) buscando pares *_metadata.json + .htm, y escribe en `output_dir`
    un archivo .md o .txt por providencia, conservando la misma estructura de
    subcarpetas (área/tema)."""
    if formato not in ("md", "txt"):
        raise ValueError("formato debe ser 'md' o 'txt'")

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    resumen = ResumenExportacion()

    for ruta_metadata in sorted(input_dir.rglob("*_metadata.json")):
        ruta_html = ruta_metadata.with_name(ruta_metadata.name.replace("_metadata.json", ".htm"))
        try:
            metadata = json.loads(ruta_metadata.read_text(encoding="utf-8"))

            if not ruta_html.exists():
                raise FileNotFoundError(f"No se encontró el HTML correspondiente: {ruta_html.name}")

            texto_plano = extraer_texto_plano(ruta_html.read_bytes())

            if formato == "md":
                contenido = construir_markdown(metadata, texto_plano)
                extension = ".md"
            else:
                contenido = construir_texto_plano_documento(metadata, texto_plano)
                extension = ".txt"

            ruta_relativa = ruta_metadata.relative_to(input_dir).parent
            carpeta_salida = output_dir / ruta_relativa
            carpeta_salida.mkdir(parents=True, exist_ok=True)

            nombre_base = ruta_html.stem
            ruta_salida = carpeta_salida / f"{nombre_base}{extension}"
            ruta_salida.write_text(contenido, encoding="utf-8")

            resumen.convertidos += 1
            logger.info("Convertido: %s -> %s", ruta_html.name, ruta_salida)

        except Exception as exc:  # noqa: BLE001 - se registra y se continúa con el resto
            logger.exception("Error convirtiendo %s", ruta_metadata)
            resumen.errores += 1
            resumen.detalles_error.append(f"{ruta_metadata}: {exc}")

    return resumen
