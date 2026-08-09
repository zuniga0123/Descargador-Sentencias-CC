"""Clasificación por reglas de palabras clave sobre el tema/subtema oficial.

Primer filtro antes de recurrir a la IA: cuenta coincidencias de palabras clave
(por área) sobre el texto combinado de los temas/subtemas oficiales (titulaciones),
el encabezado TEMA de la búsqueda y el RESUMEN. Si ningún área obtiene una
coincidencia clara, el caso se marca como ambiguo para clasificación por IA.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.classify.areas import (
    AREA_ADMINISTRATIVO,
    AREA_CONTROL_ABSTRACTO,
    AREA_DERECHOS_FUNDAMENTALES,
    AREA_ECONOMICO,
    AREA_ETNICOS,
    AREA_FAMILIA_NNA,
    AREA_LABORAL,
    AREA_PENAL,
    AREA_SALUD,
    AREA_SIN_CLASIFICAR,
    Area,
)

# Cada entrada: (área, lista de palabras/frases clave). Se buscan como substrings
# insensibles a mayúsculas sobre el texto ya normalizado (ver _normalizar).
REGLAS: list[tuple[Area, list[str]]] = [
    (
        AREA_SALUD,
        [
            "derecho a la salud", "eps", "pos", "plan obligatorio de salud",
            "sistema general de seguridad social en salud", "sgsss",
            "tutela en salud", "tratamiento medico", "tratamiento médico",
            "medicamento", "entidad promotora de salud", "ips",
            "enfermedad huerfana", "enfermedad huérfana", "cirugia", "cirugía",
            "diagnostico medico", "diagnóstico médico", "incapacidad medica",
            "incapacidad médica", "historia clinica", "historia clínica",
        ],
    ),
    (
        AREA_ETNICOS,
        [
            "consulta previa", "comunidad indigena", "comunidad indígena",
            "pueblo indigena", "pueblo indígena", "comunidad afrodescendiente",
            "comunidad negra", "territorio ancestral", "jurisdiccion especial indigena",
            "jurisdicción especial indígena", "cabildo indigena", "cabildo indígena",
            "consejo comunitario", "resguardo indigena", "resguardo indígena",
            "minorias etnicas", "minorías étnicas", "identidad cultural",
            "pueblo rrom", "comunidad rom", "diversidad etnica", "diversidad étnica",
        ],
    ),
    (
        AREA_FAMILIA_NNA,
        [
            "derechos de los niños", "derechos de las niñas", "interes superior del menor",
            "interés superior del menor", "custodia", "patria potestad", "adopcion",
            "adopción", "alimentos", "cuota alimentaria", "violencia intrafamiliar",
            "union marital de hecho", "unión marital de hecho", "regimen de visitas",
            "régimen de visitas", "menor de edad", "adolescente", "filiacion",
            "filiación", "divorcio", "custodia y cuidado personal",
        ],
    ),
    (
        AREA_PENAL,
        [
            "sistema penal acusatorio", "proceso penal", "accion de tutela contra sentencia penal",
            "fiscalia general de la nacion", "fiscalía general de la nación",
            "medida de aseguramiento", "detencion preventiva", "detención preventiva",
            "principio de legalidad penal", "delito", "juez de control de garantias",
            "juez de control de garantías", "recurso de apelacion penal",
            "casacion penal", "casación penal", "libertad condicional",
            "sistema carcelario", "sistema penitenciario", "extradicion", "extradición",
        ],
    ),
    (
        AREA_LABORAL,
        [
            "derecho al trabajo", "pension", "pensión", "reliquidacion pensional",
            "reliquidación pensional", "seguridad social", "fondo de pensiones",
            "regimen de transicion", "régimen de transición", "contrato de trabajo",
            "despido", "estabilidad laboral reforzada", "fuero sindical",
            "prima de servicios", "cesantias", "cesantías", "indemnizacion laboral",
            "indemnización laboral", "invalidez", "sustitucion pensional",
            "sustitución pensional", "riesgos laborales", "colpensiones",
        ],
    ),
    (
        AREA_ECONOMICO,
        [
            "derecho de propiedad", "regimen tributario", "régimen tributario",
            "impuesto", "servicio publico domiciliario", "servicio público domiciliario",
            "libertad economica", "libertad económica", "libre competencia",
            "expropiacion", "expropiación", "tarifa", "contrato estatal",
            "contratacion publica", "contratación pública", "propiedad privada",
            "derecho a la vivienda", "arrendamiento", "tasa", "contribucion",
            "contribución", "regalias", "regalías",
        ],
    ),
    (
        AREA_ADMINISTRATIVO,
        [
            "funcion publica", "función pública", "acto administrativo",
            "carrera administrativa", "servidor publico", "servidor público",
            "concurso de meritos", "concurso de méritos", "entidad territorial",
            "control disciplinario", "procuraduria general de la nacion",
            "procuraduría general de la nación", "contraloria general de la republica",
            "contraloría general de la república", "responsabilidad del estado",
            "nulidad y restablecimiento del derecho", "silencio administrativo",
        ],
    ),
    (
        AREA_CONTROL_ABSTRACTO,
        [
            "demanda de inconstitucionalidad", "control de constitucionalidad",
            "cosa juzgada constitucional", "inexequible", "exequible",
            "vicio de procedimiento", "vicio de forma", "juicio de constitucionalidad",
            "norma demandada", "unidad normativa", "control automatico",
            "control automático", "ley estatutaria", "decreto legislativo",
            "estado de excepcion", "estado de excepción",
        ],
    ),
    (
        AREA_DERECHOS_FUNDAMENTALES,
        [
            "debido proceso", "accion de tutela", "acción de tutela",
            "derecho de peticion", "derecho de petición", "derecho a la vida",
            "libertad de expresion", "libertad de expresión", "habeas corpus",
            "habeas data", "derecho a la intimidad", "libertad religiosa",
            "libertad de cultos", "igualdad y no discriminacion",
            "igualdad y no discriminación", "libre desarrollo de la personalidad",
            "derecho de acceso a la administracion de justicia",
            "derecho de acceso a la administración de justicia",
            "accion de cumplimiento", "acción de cumplimiento",
            "accion popular", "acción popular", "derecho a la honra",
        ],
    ),
]


@dataclass
class ResultadoClasificacionReglas:
    area: Area
    ambiguo: bool
    puntajes: dict[str, int]


def _normalizar(texto: str) -> str:
    texto = texto.lower()
    reemplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u"}
    # Se conservan tildes en las palabras clave (se comparan también sin normalizar
    # agresivamente) pero además se genera una versión sin tildes para tolerar
    # HTML con distinta codificación.
    return texto


def _contar_coincidencias(texto_normalizado: str, texto_sin_tildes: str, palabra: str) -> int:
    patron_original = re.escape(palabra.lower())
    coincidencias = len(re.findall(patron_original, texto_normalizado))
    palabra_sin_tildes = palabra.lower()
    for origen, destino in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        palabra_sin_tildes = palabra_sin_tildes.replace(origen, destino)
    if palabra_sin_tildes != palabra.lower():
        coincidencias += len(re.findall(re.escape(palabra_sin_tildes), texto_sin_tildes))
    return coincidencias


def clasificar_por_reglas(
    temas_oficiales: list[str],
    tema_busqueda: str | None = None,
    resumen: str | None = None,
) -> ResultadoClasificacionReglas:
    partes = list(temas_oficiales)
    if tema_busqueda:
        partes.append(tema_busqueda)
    if resumen:
        partes.append(resumen)
    texto = _normalizar(" \n ".join(partes))
    texto_sin_tildes = texto
    for origen, destino in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        texto_sin_tildes = texto_sin_tildes.replace(origen, destino)

    puntajes: dict[str, int] = {}
    for area, palabras_clave in REGLAS:
        total = sum(_contar_coincidencias(texto, texto_sin_tildes, palabra) for palabra in palabras_clave)
        if total:
            puntajes[area.slug] = total

    if not puntajes:
        return ResultadoClasificacionReglas(area=AREA_SIN_CLASIFICAR, ambiguo=True, puntajes=puntajes)

    ordenado = sorted(puntajes.items(), key=lambda item: item[1], reverse=True)
    mejor_slug, mejor_puntaje = ordenado[0]
    segundo_puntaje = ordenado[1][1] if len(ordenado) > 1 else 0

    # Empate o puntajes muy cercanos entre dos áreas distintas: se considera ambiguo.
    ambiguo = segundo_puntaje > 0 and mejor_puntaje - segundo_puntaje < max(1, mejor_puntaje * 0.3)

    from src.classify.areas import AREAS_POR_SLUG

    area = AREAS_POR_SLUG[mejor_slug]
    return ResultadoClasificacionReglas(area=area, ambiguo=ambiguo, puntajes=puntajes)
