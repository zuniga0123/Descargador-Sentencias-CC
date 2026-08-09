"""Clasificación por IA (API de Claude) para providencias que las reglas de palabras clave no resuelven.

Solo se invoca como último recurso, sobre el TEMA oficial + RESUMEN de la
providencia (nunca sobre el HTML completo, para mantener el costo bajo).
Requiere la variable de entorno ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import json
import logging
import re

from . import config
from .taxonomy import AREAS, SIN_CLASIFICAR

logger = logging.getLogger(__name__)


class AIClassifierError(RuntimeError):
    pass


_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    try:
        import anthropic
    except ImportError as exc:
        raise AIClassifierError(
            "El paquete 'anthropic' no está instalado. Agrega 'anthropic' a requirements.txt "
            "e instálalo, o corre con --sin-ia."
        ) from exc
    try:
        _client = anthropic.Anthropic()
    except anthropic.AnthropicError as exc:
        raise AIClassifierError(
            "No se pudo inicializar el cliente de Anthropic. Verifica que ANTHROPIC_API_KEY "
            "esté configurada, o corre con --sin-ia."
        ) from exc
    return _client


def _build_prompt(tema_oficial: str | None, subtema_oficial: str | None, resumen: str | None) -> str:
    areas_listadas = "\n".join(f"- {slug}: {label}" for slug, label in AREAS.items())
    return (
        "Eres un asistente jurídico clasificando jurisprudencia de la Corte Constitucional "
        "de Colombia en áreas del derecho de primer nivel para fines de organización documental.\n\n"
        f"Áreas disponibles (usa exactamente uno de estos identificadores):\n{areas_listadas}\n\n"
        "Datos de la providencia:\n"
        f"Tema oficial (Relatoría): {tema_oficial or '(no disponible)'}\n"
        f"Subtema oficial (Relatoría): {subtema_oficial or '(no disponible)'}\n"
        f"Resumen: {resumen or '(no disponible)'}\n\n"
        "Responde EXCLUSIVAMENTE con un JSON de una línea, sin texto adicional, con este formato:\n"
        '{"area": "<identificador-de-area>", "justificacion": "<una frase breve>"}'
    )


def classify_area_ai(
    tema_oficial: str | None,
    subtema_oficial: str | None,
    resumen: str | None,
    model: str = config.ANTHROPIC_MODEL,
) -> tuple[str, str]:
    """Devuelve (area_slug, justificacion). Lanza AIClassifierError si la llamada falla."""
    client = _get_client()
    prompt = _build_prompt(tema_oficial, subtema_oficial, resumen)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001 - cualquier fallo de API se reporta igual
        raise AIClassifierError(f"Fallo llamando a la API de Anthropic: {exc}") from exc

    texto = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()

    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if not match:
        logger.warning("Respuesta de IA sin JSON reconocible: %r", texto)
        return SIN_CLASIFICAR, "Respuesta de IA no interpretable"

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("Respuesta de IA con JSON inválido: %r", texto)
        return SIN_CLASIFICAR, "Respuesta de IA no interpretable"

    area = data.get("area")
    justificacion = data.get("justificacion", "")
    if area not in AREAS:
        logger.warning("Área devuelta por IA no reconocida: %r", area)
        return SIN_CLASIFICAR, justificacion or "Área devuelta por IA no reconocida"

    return area, justificacion
