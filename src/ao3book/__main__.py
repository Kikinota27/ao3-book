"""Línea de comandos.

    python -m ao3book                       usa ./config.toml
    python -m ao3book --config otro.toml
    python -m ao3book --format booklet      cambia el formato sin tocar el archivo
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Callable

from pypdf import PdfReader

from .booklet import impose_booklet
from .build import build_documents
from .config import FORMATS, Config, ConfigError, load_config
from .parser import list_html_files, parse_dir
from .render import render_pdf
from .split import split_works


def _page_count(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


def run(config: Config, render: Callable[..., object] = render_pdf) -> int:
    """Ejecuta el flujo completo. Devuelve el código de salida (0 = todo bien)."""
    if not config.input_dir.is_dir():
        print(f"Error: no existe la carpeta de entrada: {config.input_dir}", file=sys.stderr)
        return 1

    files = list_html_files(config.input_dir)
    if not files:
        print(f"No se encontraron obras válidas (.html) en {config.input_dir}", file=sys.stderr)
        return 1
    print(f"Procesando {len(files)} archivo(s) de entrada en {config.input_dir}...", flush=True)

    works = parse_dir(config.input_dir)
    if not works:
        print(f"No se encontraron obras válidas (.html) en {config.input_dir}", file=sys.stderr)
        return 1

    if config.split_long_works:
        try:
            works = split_works(works, config, render)
        except RuntimeError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1

    documents = build_documents(works, config)
    modo = "un solo libro" if config.combine else "un PDF por obra"
    print(f"{len(works)} obra(s), formato {config.format}, {modo}:", flush=True)

    failures = 0
    for doc in documents:
        out = config.output_dir / f"{doc.name}.pdf"
        out.parent.mkdir(parents=True, exist_ok=True)
        try:
            if config.is_booklet:
                with tempfile.TemporaryDirectory() as tmp:
                    plain = Path(tmp) / f"{doc.name}.pdf"
                    render(doc.html, plain)
                    pages = _page_count(plain)
                    impose_booklet(plain, out, config.sheet_size_mm)
                info = f"{pages} páginas -> {_page_count(out) // 2} hojas a doble cara"
            else:
                render(doc.html, out)
                info = f"{_page_count(out)} páginas"
        except RuntimeError as error:  # p. ej. WeasyPrint no instalado: no tiene sentido seguir
            print(f"Error: {error}", file=sys.stderr)
            return 1
        except Exception as error:  # noqa: BLE001 - se informa y se sigue con el resto
            failures += 1
            print(f"[error] {doc.name}: {error}", file=sys.stderr)
            continue
        print(f"  {out}  ({info})", flush=True)

    return 1 if failures else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ao3book",
        description="Convierte descargas HTML de AO3 en un PDF imprimible con formato de libro.",
    )
    parser.add_argument("--config", default="config.toml", metavar="ARCHIVO",
                        help="archivo de configuración (por defecto: config.toml)")
    parser.add_argument("--format", type=str.lower, choices=FORMATS,
                        help="reemplaza el formato definido en la configuración")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.config)
        if args.format:
            config = config.with_format(args.format)
    except ConfigError as error:
        print(f"Error de configuración: {error}", file=sys.stderr)
        return 1
    return run(config)


if __name__ == "__main__":
    sys.exit(main())
