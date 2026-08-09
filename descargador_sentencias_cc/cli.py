"""Interfaz de línea de comandos."""

from __future__ import annotations

import argparse
import logging
import sys
import urllib.robotparser
from pathlib import Path

from bs4 import BeautifulSoup

from . import config
from .http_client import RateLimitedClient
from .pipeline import run_pipeline
from .search import SearchParams

logger = logging.getLogger(__name__)


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--rate-limit", type=float, default=config.RATE_LIMIT_SECONDS,
        help=f"Segundos mínimos entre solicitudes (default: {config.RATE_LIMIT_SECONDS}).",
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Nivel de logging (default: INFO).",
    )


def cmd_descargar(args: argparse.Namespace) -> int:
    out_dir = args.out_dir
    db_path = args.db or str(Path(out_dir) / config.DEFAULT_DB_FILENAME)

    params = SearchParams(
        buscar_por=args.tema,
        finicio=args.desde,
        ffin=args.hasta,
        search_option=args.search_option,
        cant_providencias=args.cant_providencias,
    )

    stats = run_pipeline(
        params=params,
        out_dir=out_dir,
        db_path=db_path,
        use_ai=not args.sin_ia,
        incremental=args.incremental,
        force=args.force,
        rate_limit_seconds=args.rate_limit,
    )

    print("\nResumen de la corrida:")
    for clave, valor in stats.items():
        print(f"  {clave}: {valor}")
    print(f"\nÍndice SQLite: {db_path}")
    print(f"Archivos en: {Path(out_dir) / config.CORTE_SLUG}")
    return 0


def cmd_inspeccionar_formulario(args: argparse.Namespace) -> int:
    """Vuelca la estructura del formulario del buscador: útil para confirmar valores reales
    de searchOption y otros campos antes de una corrida grande (brief, sección 5, paso 1)."""
    client = RateLimitedClient(rate_limit_seconds=args.rate_limit)
    html = client.get_text(config.BUSCADOR_URL)
    soup = BeautifulSoup(html, "lxml")

    selects = soup.find_all("select")
    if not selects:
        print("No se encontraron elementos <select> en la página del buscador.")
    for select in selects:
        nombre = select.get("name") or select.get("id") or "(sin nombre)"
        print(f"\n<select name/id={nombre!r}>")
        for option in select.find_all("option"):
            valor = option.get("value", "")
            texto = option.get_text(strip=True)
            print(f"  value={valor!r}  texto={texto!r}")

    forms = soup.find_all("form")
    print(f"\nFormularios encontrados: {len(forms)}")
    for form in forms:
        print(f"  action={form.get('action')!r} method={form.get('method')!r}")

    return 0


def cmd_verificar_robots(args: argparse.Namespace) -> int:
    client = RateLimitedClient(rate_limit_seconds=args.rate_limit)
    texto = client.get_text(config.ROBOTS_URL)
    print(texto)

    parser = urllib.robotparser.RobotFileParser()
    parser.parse(texto.splitlines())

    rutas_prueba = [config.BUSCADOR_URL, f"{config.BASE_URL}/relatoria/2019/T-388-19.htm"]
    print("\nEvaluación para user-agent", repr(config.USER_AGENT))
    for ruta in rutas_prueba:
        permitido = parser.can_fetch(config.USER_AGENT, ruta)
        print(f"  can_fetch({ruta!r}) = {permitido}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="descargador-sentencias-cc",
        description="Descarga y clasifica providencias de la Corte Constitucional de Colombia.",
    )
    subparsers = parser.add_subparsers(dest="comando", required=True)

    p_descargar = subparsers.add_parser("descargar", help="Busca, descarga y clasifica providencias.")
    p_descargar.add_argument("--tema", required=True, help="Término de búsqueda (buscar_por).")
    p_descargar.add_argument("--desde", required=True, help="Fecha inicial YYYY-MM-DD (finicio).")
    p_descargar.add_argument("--hasta", required=True, help="Fecha final YYYY-MM-DD (ffin).")
    p_descargar.add_argument(
        "--search-option", default=config.SEARCH_OPTIONS["texto_providencia"],
        help="Valor de searchOption del buscador (default: modo texto de providencias, confirmado).",
    )
    p_descargar.add_argument(
        "--cant-providencias", type=int, default=config.CANT_PROVIDENCIAS_DEFAULT,
        help=f"Máximo de resultados a traer, hasta {config.CANT_PROVIDENCIAS_MAX}.",
    )
    p_descargar.add_argument("--out-dir", default=config.DEFAULT_OUTPUT_DIR, help="Carpeta de salida.")
    p_descargar.add_argument("--db", default=None, help="Ruta al índice SQLite (default: <out-dir>/indice.sqlite).")
    p_descargar.add_argument("--sin-ia", action="store_true", help="Desactiva la clasificación por IA de respaldo.")
    p_descargar.add_argument(
        "--incremental", action="store_true",
        help="Ajusta la fecha inicial a la última fecha de publicación ya indexada.",
    )
    p_descargar.add_argument(
        "--force", action="store_true", help="Vuelve a descargar providencias ya presentes en el índice.",
    )
    _add_common_args(p_descargar)
    p_descargar.set_defaults(func=cmd_descargar)

    p_inspeccionar = subparsers.add_parser(
        "inspeccionar-formulario",
        help="Vuelca los <select>/<form> del buscador para calibrar searchOption y otros parámetros.",
    )
    _add_common_args(p_inspeccionar)
    p_inspeccionar.set_defaults(func=cmd_inspeccionar_formulario)

    p_robots = subparsers.add_parser("verificar-robots", help="Descarga y evalúa robots.txt del sitio.")
    _add_common_args(p_robots)
    p_robots.set_defaults(func=cmd_verificar_robots)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
