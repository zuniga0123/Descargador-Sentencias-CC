"""Convierte las providencias descargadas a Markdown/texto plano para subir a
SharePoint/OneDrive como base de conocimiento de un agente de Copilot.

No consulta el sitio de la Corte Constitucional: solo lee lo que ya descargó
src.cli en la carpeta `jurisprudencia/`.

Ejemplo:
    python -m src.export_copilot --input-dir jurisprudencia --output-dir jurisprudencia_copilot
    python -m src.export_copilot --formato txt
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src import config
from src.export.markdown import exportar_carpeta


def _parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="export-copilot",
        description="Convierte las providencias descargadas (HTML+metadata.json) a Markdown/texto plano "
        "para subir a SharePoint/OneDrive como base de conocimiento de un agente de Copilot.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=config.DEFAULT_OUTPUT_DIR,
        help="Carpeta de entrada generada por el descargador (por defecto 'jurisprudencia').",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=config.PROJECT_ROOT / "jurisprudencia_copilot",
        help="Carpeta de salida donde se escriben los archivos convertidos.",
    )
    parser.add_argument(
        "--formato",
        choices=["md", "txt"],
        default="md",
        help="Formato de salida (por defecto md).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Log detallado (DEBUG).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parsear_argumentos(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not args.input_dir.exists():
        print(f"No existe la carpeta de entrada: {args.input_dir}", file=sys.stderr)
        return 1

    resumen = exportar_carpeta(args.input_dir, args.output_dir, formato=args.formato)

    print(
        f"\nResumen: {resumen.convertidos} convertidos | {resumen.errores} con error"
        f"\nArchivos escritos en: {args.output_dir}"
    )
    if resumen.detalles_error:
        print("Errores:")
        for detalle in resumen.detalles_error:
            print(f"  - {detalle}")

    return 1 if resumen.errores and not resumen.convertidos else 0


if __name__ == "__main__":
    sys.exit(main())
