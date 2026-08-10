"""CLI del descargador y clasificador de jurisprudencia de la Corte Constitucional.

Ejemplos:
    python -m src.cli --buscar-por "T-388 DE 2019" --finicio 2019-01-01 --ffin 2019-12-31
    python -m src.cli --buscar-por "LIBERTAD DE EXPRESION" --incremental
    python -m src.cli --buscar-por "T-388 DE 2019" --dry-run --no-ia

    # Todas las sentencias de Tutela, Constitucionalidad y Unificación de los últimos 7 años:
    python -m src.cli --tipos T,SU,C --ultimos-anios 7
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from pathlib import Path

from src import config
from src.pipeline import ejecutar, ejecutar_por_tipos_y_anios
from src.scraper.search import TIPOS_PROVIDENCIA


def _parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="descargador-sentencias-cc",
        description="Descarga, clasifica e indexa providencias de la Corte Constitucional de Colombia.",
    )
    parser.add_argument(
        "--buscar-por",
        default=None,
        help="Término de búsqueda (ej. 'T-388 DE 2019', un tema, o vacío '' para rango de fechas amplio). "
        "No se usa junto con --tipos/--anios.",
    )
    parser.add_argument("--finicio", default=None, help="Fecha inicial YYYY-MM-DD (por defecto 1992-01-01).")
    parser.add_argument("--ffin", default=None, help="Fecha final YYYY-MM-DD (por defecto hoy).")
    parser.add_argument(
        "--search-option",
        default=config.DEFAULT_SEARCH_OPTION,
        help=f"Modo de búsqueda del buscador (por defecto {config.DEFAULT_SEARCH_OPTION}). Solo aplica con --buscar-por.",
    )
    parser.add_argument(
        "--tipos",
        default=None,
        help="Alternativa a --buscar-por: trae TODAS las providencias de uno o más tipos, separados por "
        f"coma. Valores válidos: {', '.join(TIPOS_PROVIDENCIA)} (ej. 'T,SU,C' para tutelas, sentencias de "
        "unificación y de constitucionalidad, sin incluir Autos). Requiere --anios o --ultimos-anios.",
    )
    parser.add_argument(
        "--anios",
        default=None,
        help="Años de sentencia a traer con --tipos, separados por coma (ej. '2019,2020,2021').",
    )
    parser.add_argument(
        "--ultimos-anios",
        type=int,
        default=None,
        help="Alternativa a --anios: los últimos N años (incluyendo el actual). Ej. --ultimos-anios 7.",
    )
    parser.add_argument(
        "--cant-providencias",
        type=int,
        default=config.DEFAULT_CANT_PROVIDENCIAS,
        help=f"Máximo de resultados a solicitar al buscador (tope {config.MAX_CANT_PROVIDENCIAS}).",
    )
    parser.add_argument("--max-resultados", type=int, default=None, help="Límite adicional para pruebas.")
    parser.add_argument(
        "--output-dir", type=Path, default=config.DEFAULT_OUTPUT_DIR, help="Carpeta raíz de salida."
    )
    parser.add_argument("--db-path", type=Path, default=config.DEFAULT_DB_PATH, help="Ruta del índice SQLite.")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Solo descarga providencias nuevas desde la última fecha de publicación registrada en el índice.",
    )
    parser.add_argument(
        "--forzar-reprocesar",
        action="store_true",
        help="Vuelve a descargar y clasificar providencias que ya están en el índice.",
    )
    parser.add_argument(
        "--no-ia",
        action="store_true",
        help="Desactiva la clasificación por IA (solo reglas de palabras clave).",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=config.DEFAULT_RATE_LIMIT_SECONDS,
        help="Segundos mínimos entre solicitudes al sitio.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la ejecución sin descargar HTML ni escribir en disco/DB (aún consulta el buscador).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Log detallado (DEBUG).")
    return parser.parse_args(argv)


def _resolver_anios(args: argparse.Namespace) -> list[int]:
    if args.ultimos_anios is not None:
        anio_actual = dt.date.today().year
        return list(range(anio_actual - args.ultimos_anios + 1, anio_actual + 1))
    if args.anios:
        return [int(a.strip()) for a in args.anios.split(",") if a.strip()]
    raise SystemExit("--tipos requiere --anios o --ultimos-anios.")


def main(argv: list[str] | None = None) -> int:
    args = _parsear_argumentos(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.tipos and args.buscar_por:
        raise SystemExit("Use --buscar-por o --tipos/--anios, no ambos a la vez.")

    if args.tipos:
        tipos = [t.strip().upper() for t in args.tipos.split(",") if t.strip()]
        desconocidos = [t for t in tipos if t not in TIPOS_PROVIDENCIA]
        if desconocidos:
            raise SystemExit(
                f"Tipo(s) no reconocido(s): {', '.join(desconocidos)}. "
                f"Valores válidos: {', '.join(TIPOS_PROVIDENCIA)}."
            )
        anios = _resolver_anios(args)
        resumen = ejecutar_por_tipos_y_anios(
            tipos=tipos,
            anios=anios,
            output_dir=args.output_dir,
            db_path=args.db_path,
            usar_ia=not args.no_ia,
            max_resultados=args.max_resultados,
            rate_limit_seconds=args.rate_limit,
            dry_run=args.dry_run,
            forzar_reprocesar=args.forzar_reprocesar,
        )
    elif args.buscar_por is not None:
        resumen = ejecutar(
            buscar_por=args.buscar_por,
            finicio=args.finicio,
            ffin=args.ffin,
            search_option=args.search_option,
            cant_providencias=args.cant_providencias,
            output_dir=args.output_dir,
            db_path=args.db_path,
            incremental=args.incremental,
            usar_ia=not args.no_ia,
            max_resultados=args.max_resultados,
            rate_limit_seconds=args.rate_limit,
            dry_run=args.dry_run,
            forzar_reprocesar=args.forzar_reprocesar,
        )
    else:
        raise SystemExit("Debe indicar --buscar-por, o bien --tipos junto con --anios/--ultimos-anios.")

    print(
        f"\nResumen: {resumen.encontradas} encontradas | "
        f"{resumen.nuevas} nuevas | {resumen.actualizadas} actualizadas | "
        f"{resumen.saltadas} omitidas | {resumen.errores} con error"
    )
    if resumen.detalles_error:
        print("Errores:")
        for detalle in resumen.detalles_error:
            print(f"  - {detalle}")

    return 1 if resumen.errores and not (resumen.nuevas or resumen.actualizadas) else 0


if __name__ == "__main__":
    sys.exit(main())
