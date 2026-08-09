"""Áreas de primer nivel para agrupar la taxonomía oficial de temas/subtemas.

La Corte Constitucional no clasifica por área tradicional del derecho (civil,
laboral, penal), sino por derechos y figuras constitucionales. Este primer nivel
es una propuesta de agrupación para la estructura de carpetas; los niveles
"tema" y "subtema" reales siempre son los oficiales de la Relatoría.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Area:
    slug: str
    nombre: str


AREA_DERECHOS_FUNDAMENTALES = Area("derechos-fundamentales-debido-proceso", "Derechos Fundamentales y Debido Proceso")
AREA_CONTROL_ABSTRACTO = Area("control-constitucionalidad-abstracto", "Control de Constitucionalidad Abstracto")
AREA_LABORAL = Area("derecho-laboral-seguridad-social", "Derecho Laboral y Seguridad Social")
AREA_FAMILIA_NNA = Area("derecho-familia-nna", "Derecho de Familia y Derechos de Niños, Niñas y Adolescentes")
AREA_PENAL = Area("derecho-penal-sistema-acusatorio", "Derecho Penal y Sistema Acusatorio")
AREA_ADMINISTRATIVO = Area("derecho-administrativo-funcion-publica", "Derecho Administrativo y Función Pública")
AREA_ECONOMICO = Area("derecho-constitucional-economico", "Derecho Constitucional Económico")
AREA_ETNICOS = Area("derechos-etnicos-consulta-previa", "Derechos Étnicos y Consulta Previa")
AREA_SALUD = Area("derecho-a-la-salud", "Derecho a la Salud")
AREA_SIN_CLASIFICAR = Area("otros-sin-clasificar", "Otros / Sin clasificar")

AREAS: list[Area] = [
    AREA_DERECHOS_FUNDAMENTALES,
    AREA_CONTROL_ABSTRACTO,
    AREA_LABORAL,
    AREA_FAMILIA_NNA,
    AREA_PENAL,
    AREA_ADMINISTRATIVO,
    AREA_ECONOMICO,
    AREA_ETNICOS,
    AREA_SALUD,
    AREA_SIN_CLASIFICAR,
]

AREAS_POR_SLUG: dict[str, Area] = {area.slug: area for area in AREAS}
