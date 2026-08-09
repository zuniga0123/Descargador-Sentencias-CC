"""Orquesta la clasificación: reglas de palabras clave primero, IA como respaldo."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.classify.ai_classifier import clasificar_con_ia
from src.classify.areas import AREA_SIN_CLASIFICAR, Area
from src.classify.rules import clasificar_por_reglas

logger = logging.getLogger(__name__)


@dataclass
class ResultadoClasificacion:
    area: Area
    metodo: str  # "reglas" | "ia" | "sin_clasificar"
    justificacion: str | None = None


def clasificar(
    temas_oficiales: list[str],
    tema_busqueda: str | None,
    resumen: str | None,
    numero_providencia: str,
    usar_ia: bool = True,
) -> ResultadoClasificacion:
    resultado_reglas = clasificar_por_reglas(temas_oficiales, tema_busqueda, resumen)

    if not resultado_reglas.ambiguo:
        return ResultadoClasificacion(area=resultado_reglas.area, metodo="reglas")

    if usar_ia:
        resultado_ia = clasificar_con_ia(
            temas_oficiales=temas_oficiales,
            tema_busqueda=tema_busqueda,
            resumen=resumen,
            numero_providencia=numero_providencia,
        )
        if resultado_ia is not None:
            area, justificacion = resultado_ia
            return ResultadoClasificacion(area=area, metodo="ia", justificacion=justificacion)

    # Sin IA disponible o sin resultado claro: se usa la mejor sugerencia de las
    # reglas si hubo alguna coincidencia, o "sin clasificar" para revisión manual.
    if resultado_reglas.puntajes:
        return ResultadoClasificacion(area=resultado_reglas.area, metodo="reglas_ambiguo")
    return ResultadoClasificacion(area=AREA_SIN_CLASIFICAR, metodo="sin_clasificar")
