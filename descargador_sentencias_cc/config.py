"""Configuración y constantes del descargador de jurisprudencia de la Corte Constitucional."""

from __future__ import annotations

BASE_URL = "https://www.corteconstitucional.gov.co"
BUSCADOR_PATH = "/relatoria/buscador_new/"
BUSCADOR_URL = f"{BASE_URL}{BUSCADOR_PATH}"
ROBOTS_URL = f"{BASE_URL}/robots.txt"

USER_AGENT = (
    "descargador-sentencias-cc/0.1 "
    "(uso academico/investigacion; contacto: cz122402@gmail.com)"
)

# Ritmo de solicitudes: brief pide 1-2s entre requests.
RATE_LIMIT_SECONDS = 1.5
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 4
BACKOFF_FACTOR = 2.0  # segundos: 2, 4, 8, 16...

# Valor confirmado manualmente contra el buscador real (ver brief, sección 2).
# El resto de opciones del combo "Buscar en" NO están confirmadas: hay que
# abrir el buscador en un navegador, probar cada opción y capturar el valor
# real de `searchOption` en la URL resultante, y actualizar este diccionario.
SEARCH_OPTIONS = {
    "texto_providencia": "prov_sentencia",  # confirmado
    # "temas_subtema": "TODO_confirmar",
    # "texto_resuelve": "TODO_confirmar",
    # "normas_demandadas": "TODO_confirmar",
    # "numero_providencia": "TODO_confirmar",
}

ORDERBY_DEFAULT = "des__score"
CANT_PROVIDENCIAS_DEFAULT = 500
CANT_PROVIDENCIAS_MAX = 5000

DEFAULT_OUTPUT_DIR = "jurisprudencia"
DEFAULT_DB_FILENAME = "indice.sqlite"
CORTE_SLUG = "corte-constitucional"

ANTHROPIC_MODEL = "claude-sonnet-5"
