"""Clasificador de respaldo por IA (API de Anthropic) para casos ambiguos.

Solo se invoca cuando la clasificación por reglas de palabras clave (rules.py)
no da un resultado claro. Requiere la variable de entorno ANTHROPIC_API_KEY;
si no está configurada, se degrada con gracia devolviendo None (el caso queda
marcado como "otros-sin-clasificar" para revisión manual).
"""

from __future__ import annotations

import logging
import os

from src.classify.areas import AREAS, AREA_SIN_CLASIFICAR, AREAS_POR_SLUG, Area

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.environ.get("ANTHROPIC_CLASSIFIER_MODEL", "claude-haiku-4-5-20251001")

_TOOL_NAME = "clasificar_area"


def _slugs_disponibles() -> list[str]:
    return [area.slug for area in AREAS if area is not AREA_SIN_CLASIFICAR]


def api_key_disponible() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _construir_tool_definition() -> dict:
    slugs = _slugs_disponibles()
    descripciones = "\n".join(f"- {area.slug}: {area.nombre}" for area in AREAS if area is not AREA_SIN_CLASIFICAR)
    return {
        "name": _TOOL_NAME,
        "description": (
            "Registra el área de primer nivel del derecho constitucional colombiano "
            "que mejor agrupa la providencia descrita.\n\nÁreas disponibles:\n" + descripciones
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "area_slug": {
                    "type": "string",
                    "enum": slugs,
                    "description": "Slug del área elegida.",
                },
                "justificacion": {
                    "type": "string",
                    "description": "Justificación breve (1-2 frases) de la elección.",
                },
            },
            "required": ["area_slug", "justificacion"],
        },
    }


def clasificar_con_ia(
    temas_oficiales: list[str],
    tema_busqueda: str | None,
    resumen: str | None,
    numero_providencia: str,
    model: str = DEFAULT_MODEL,
) -> tuple[Area, str] | None:
    """Devuelve (área, justificación) o None si no hay API key o falla la llamada."""
    if not api_key_disponible():
        logger.info(
            "ANTHROPIC_API_KEY no configurada: %s queda sin clasificación por IA (revisión manual).",
            numero_providencia,
        )
        return None

    try:
        import anthropic
    except ImportError:
        logger.warning("El paquete 'anthropic' no está instalado; omitiendo clasificación por IA.")
        return None

    partes = []
    if tema_busqueda:
        partes.append(f"TEMA (encabezado del buscador): {tema_busqueda}")
    if temas_oficiales:
        partes.append("Temas/subtemas oficiales de la Relatoría:\n- " + "\n- ".join(temas_oficiales))
    if resumen:
        partes.append(f"RESUMEN: {resumen}")
    contexto = "\n\n".join(partes) if partes else "(sin metadatos disponibles)"

    prompt = (
        f"Providencia de la Corte Constitucional de Colombia: {numero_providencia}\n\n"
        f"{contexto}\n\n"
        "Clasifica esta providencia en UNA sola área de primer nivel usando la herramienta "
        f"'{_TOOL_NAME}'."
    )

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=300,
            tools=[_construir_tool_definition()],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception:
        logger.exception("Fallo la llamada a la API de Anthropic para %s", numero_providencia)
        return None

    for bloque in response.content:
        if getattr(bloque, "type", None) == "tool_use" and bloque.name == _TOOL_NAME:
            area_slug = bloque.input.get("area_slug")
            justificacion = bloque.input.get("justificacion", "")
            area = AREAS_POR_SLUG.get(area_slug)
            if area is None:
                logger.warning("La IA devolvió un area_slug desconocido: %s", area_slug)
                return None
            return area, justificacion

    logger.warning("La respuesta de la IA no incluyó una llamada a la herramienta esperada.")
    return None
