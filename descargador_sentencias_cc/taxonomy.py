"""Clasificación por reglas de palabras clave sobre el tema/subtema oficial de la Relatoría.

La Corte Constitucional NO clasifica por área del derecho tradicional (civil,
laboral, penal); usa derechos y figuras constitucionales. Este módulo agrupa
esa taxonomía oficial (tema/subtema, que se usa tal cual) bajo 10 áreas de
primer nivel propuestas en el brief, mediante reglas de palabras clave. Los
casos que ninguna regla resuelva quedan en 'sin_clasificar' para revisión
manual o clasificación por IA (ver ai_classifier.py).

Las listas de palabras clave son un punto de partida razonable, no una
taxonomía validada por un experto legal: conviene revisarlas con muestras
reales y ajustarlas con el tiempo.
"""

from __future__ import annotations

from .utils import strip_accents

SIN_CLASIFICAR = "otros-sin-clasificar"

# Orden: (slug, etiqueta legible). El orden importa para AREA_RULES (más
# específico primero) pero no para este catálogo.
AREAS: dict[str, str] = {
    "derechos-fundamentales-debido-proceso": "Derechos Fundamentales y Debido Proceso",
    "control-constitucionalidad-abstracto": "Control de Constitucionalidad Abstracto",
    "derecho-laboral-seguridad-social": "Derecho Laboral y Seguridad Social",
    "derecho-familia-ninez": "Derecho de Familia y Derechos de Niños, Niñas y Adolescentes",
    "derecho-penal-sistema-acusatorio": "Derecho Penal y Sistema Acusatorio",
    "derecho-administrativo-funcion-publica": "Derecho Administrativo y Función Pública",
    "derecho-constitucional-economico": "Derecho Constitucional Económico",
    "derechos-etnicos-consulta-previa": "Derechos Étnicos y Consulta Previa",
    "derecho-a-la-salud": "Derecho a la Salud",
    SIN_CLASIFICAR: "Otros / Sin clasificar",
}

# Reglas en orden de prioridad: se evalúan de arriba a abajo y se devuelve la
# primera área cuyas palabras clave aparezcan en el texto. Las áreas más
# específicas van primero para que no las absorba el fallback genérico de
# "Derechos Fundamentales y Debido Proceso".
AREA_RULES: list[tuple[str, list[str]]] = [
    (
        "derecho-a-la-salud",
        ["SALUD", "EPS", "PLAN OBLIGATORIO DE SALUD", "IPS", "MEDICAMENTO",
         "TRATAMIENTO MEDICO", "SEGURIDAD SOCIAL EN SALUD"],
    ),
    (
        "derechos-etnicos-consulta-previa",
        ["CONSULTA PREVIA", "COMUNIDAD INDIGENA", "PUEBLO INDIGENA", "COMUNIDAD AFRODESCENDIENTE",
         "COMUNIDAD NEGRA", "TERRITORIO ANCESTRAL", "JURISDICCION ESPECIAL INDIGENA",
         "MINORIA ETNICA", "PUEBLO ROM", "COMUNIDAD PALENQUERA"],
    ),
    (
        "derecho-familia-ninez",
        ["MENOR DE EDAD", "NINO", "NINA", "ADOLESCENTE", "INTERES SUPERIOR DEL MENOR",
         "CUSTODIA", "PATRIA POTESTAD", "CUOTA DE ALIMENTOS", "ADOPCION", "UNION MARITAL",
         "DERECHO DE FAMILIA"],
    ),
    (
        "derecho-laboral-seguridad-social",
        ["PENSION", "DESPIDO", "CONTRATO DE TRABAJO", "TRABAJADOR", "EMPLEADOR",
         "FUERO SINDICAL", "PRESTACIONES SOCIALES", "ACOSO LABORAL", "REGIMEN PENSIONAL"],
    ),
    (
        "derecho-penal-sistema-acusatorio",
        ["SISTEMA ACUSATORIO", "PROCESO PENAL", "IMPUTACION", "DELITO", "FISCALIA",
         "DETENCION PREVENTIVA", "EXTINCION DE DOMINIO", "CAPTURA"],
    ),
    (
        "derecho-constitucional-economico",
        ["REGIMEN TRIBUTARIO", "IMPUESTO", "SERVICIOS PUBLICOS DOMICILIARIOS", "TARIFA",
         "LIBERTAD ECONOMICA", "LIBRE COMPETENCIA", "EXPROPIACION", "PROPIEDAD PRIVADA"],
    ),
    (
        "derecho-administrativo-funcion-publica",
        ["FUNCION PUBLICA", "CARRERA ADMINISTRATIVA", "ACTO ADMINISTRATIVO", "SERVIDOR PUBLICO",
         "CONTRATACION ESTATAL", "EMPLEADO PUBLICO", "DESTITUCION"],
    ),
    (
        "control-constitucionalidad-abstracto",
        ["DEMANDA DE INCONSTITUCIONALIDAD", "CONTROL DE CONSTITUCIONALIDAD", "INEXEQUIBLE", "EXEQUIBLE"],
    ),
    (
        "derechos-fundamentales-debido-proceso",
        ["DEBIDO PROCESO", "DERECHOS FUNDAMENTALES", "ACCION DE TUTELA", "DERECHO DE PETICION",
         "MINIMO VITAL", "DIGNIDAD HUMANA", "ACCESO A LA ADMINISTRACION DE JUSTICIA"],
    ),
]


def _normalize(text: str | None) -> str:
    return strip_accents(text or "").upper()


def classify_area_by_rules(
    tema_oficial: str | None,
    subtema_oficial: str | None,
    resumen: str | None,
) -> str | None:
    """Devuelve el slug del área según las reglas de palabras clave, o None si ninguna aplica."""
    texto = _normalize(f"{tema_oficial or ''} {subtema_oficial or ''} {resumen or ''}")
    if not texto.strip():
        return None
    for area_slug, keywords in AREA_RULES:
        if any(keyword in texto for keyword in keywords):
            return area_slug
    return None
