"""Carga y validación de config.toml, y tamaños de página."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

# Tamaños de hoja vertical (ancho, alto) en mm
PAGE_SIZES_MM: dict[str, tuple[float, float]] = {
    "a4": (210.0, 297.0),
    "a5": (148.0, 210.0),
    "letter": (215.9, 279.4),
}
SHEETS = ("a4", "letter")  # hojas físicas válidas para folleto
FORMATS = ("a4", "a5", "letter", "booklet")

# Márgenes (mm) según el tamaño de la página lógica (inner = lomo)
_MARGINS_SMALL = {"top": 16.0, "bottom": 18.0, "inner": 20.0, "outer": 14.0}
_MARGINS_LARGE = {"top": 22.0, "bottom": 24.0, "inner": 28.0, "outer": 20.0}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    input_dir: Path = Path("input")
    output_dir: Path = Path("output")
    format: str = "a5"
    combine: bool = True
    start_on_recto: bool = True
    toc_on_recto: bool = False
    font_family: str = "Georgia, 'Times New Roman', serif"
    font_size: str = "11pt"
    line_height: float = 1.45
    booklet_sheet: str = "a4"
    split_long_works: bool = False
    max_pages_per_part: int = 400

    @property
    def is_booklet(self) -> bool:
        return self.format == "booklet"

    @property
    def page_size_mm(self) -> tuple[float, float]:
        """Tamaño de la página lógica (ancho, alto) en mm."""
        if self.is_booklet:
            w, h = PAGE_SIZES_MM[self.booklet_sheet]
            return (h / 2, w)  # mitad de la hoja apaisada
        return PAGE_SIZES_MM[self.format]

    @property
    def sheet_size_mm(self) -> tuple[float, float]:
        """Hoja física apaisada (ancho, alto) en mm; solo para folleto."""
        w, h = PAGE_SIZES_MM[self.booklet_sheet]
        return (h, w)

    @property
    def margins_mm(self) -> dict[str, float]:
        """Márgenes (top, bottom, inner, outer) según el tamaño de la página."""
        w, _ = self.page_size_mm
        return dict(_MARGINS_SMALL if w < 180 else _MARGINS_LARGE)

    def page_css(self) -> str:
        """Bloque @page con tamaño y márgenes espejados (lomo mayor que el borde).

        Se genera con los números ya resueltos porque var() dentro de @page no es
        confiable en todos los motores.
        """
        w, h = self.page_size_mm
        m = self.margins_mm
        return (
            f"@page {{ size: {w:g}mm {h:g}mm; margin-top: {m['top']:g}mm; margin-bottom: {m['bottom']:g}mm; }}\n"
            f"@page :left {{ margin-left: {m['outer']:g}mm; margin-right: {m['inner']:g}mm; }}\n"
            f"@page :right {{ margin-left: {m['inner']:g}mm; margin-right: {m['outer']:g}mm; }}\n"
        )

    def css_vars(self) -> dict[str, str]:
        """Variables de tipografía que se inyectan en :root."""
        return {
            "font-family": self.font_family,
            "font-size": self.font_size,
            "line-height": f"{self.line_height:g}",
        }

    def with_format(self, fmt: str) -> "Config":
        """Copia con otro formato (override desde la CLI)."""
        return _validate(replace(self, format=fmt.lower()))


def _validate(cfg: Config) -> Config:
    if cfg.format not in FORMATS:
        raise ConfigError(f"format '{cfg.format}' inválido. Opciones: {', '.join(FORMATS)}")
    if cfg.booklet_sheet not in SHEETS:
        raise ConfigError(f"booklet.sheet '{cfg.booklet_sheet}' inválido. Opciones: {', '.join(SHEETS)}")
    if cfg.line_height <= 0:
        raise ConfigError("line_height debe ser mayor que 0")
    if cfg.max_pages_per_part < 1:
        raise ConfigError("max_pages_per_part debe ser mayor que 0")
    return cfg


def load_config(path: str | Path = "config.toml") -> Config:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"No existe el archivo de configuración: {path}")
    with path.open("rb") as f:
        data = tomllib.load(f)

    base = path.resolve().parent  # las rutas son relativas al config.toml
    inp, book, booklet = data.get("input", {}), data.get("book", {}), data.get("booklet", {})
    defaults = Config()

    cfg = Config(
        input_dir=base / inp.get("dir", defaults.input_dir),
        output_dir=base / inp.get("output_dir", defaults.output_dir),
        format=str(book.get("format", defaults.format)).lower(),
        combine=bool(book.get("combine", defaults.combine)),
        start_on_recto=bool(book.get("start_on_recto", defaults.start_on_recto)),
        toc_on_recto=bool(book.get("toc_on_recto", defaults.toc_on_recto)),
        font_family=book.get("font_family", defaults.font_family),
        font_size=book.get("font_size", defaults.font_size),
        line_height=float(book.get("line_height", defaults.line_height)),
        booklet_sheet=str(booklet.get("sheet", defaults.booklet_sheet)).lower(),
        split_long_works=bool(book.get("split_long_works", defaults.split_long_works)),
        max_pages_per_part=int(book.get("max_pages_per_part", defaults.max_pages_per_part)),
    )
    return _validate(cfg)
