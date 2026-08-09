"""Configuración y constantes del buscador de la Relatoría de la Corte Constitucional."""

from pathlib import Path

BASE_HOST = "https://www.corteconstitucional.gov.co"
BUSCADOR_BASE = f"{BASE_HOST}/relatoria/buscador_new/"
BUSCADOR_INDEX = f"{BUSCADOR_BASE}index.php"

# robots.txt (verificado 2026-08-09): Allow: /relatoria/ ; no está en la lista Disallow.
ROBOTS_URL = f"{BASE_HOST}/robots.txt"

# El botón "Exportar a Excel" del buscador está bloqueado por el WAF del sitio
# (POST a views/search/result_export_excel.php devuelve "The URL you requested
# has been blocked" incluso con headers de navegador). Por eso se usa scraping HTML.
EXPORT_EXCEL_BLOCKED = True

USER_AGENT = (
    "Mozilla/5.0 (compatible; JurisprudenciaCorteBot/0.1; "
    "+scraper de investigacion academica, ver README del proyecto)"
)
# NOTA: el WAF del sitio bloquea (HTTP 500 "The URL you requested has been
# blocked") cualquier User-Agent que contenga la subcadena "CCBot" (coincide
# con el crawler de Common Crawl), y también rechaza user-agents que no
# empiecen por un token tipo navegador ("Mozilla/5.0 (...)"). Verificado
# manualmente el 2026-08-09; no cambiar sin volver a probar contra el sitio.

DEFAULT_RATE_LIMIT_SECONDS = 1.5
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 4
DEFAULT_BACKOFF_BASE_SECONDS = 2.0

# Límite documentado del buscador para cant_providencias.
MAX_CANT_PROVIDENCIAS = 5000
DEFAULT_CANT_PROVIDENCIAS = 500

DEFAULT_SEARCH_OPTION = "prov_sentencia"
DEFAULT_ORDER_BY = "des__score"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "jurisprudencia"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "indice.sqlite"

CORTE_SLUG = "corte-constitucional"
