"""Carga y validación de config.toml, y tamaños de página."""
from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path

# Constantes de formato y márgenes de referencia (inner = lomo, en mm)
BOOKLET_FORMAT = "booklet"
DEFAULT_FORMAT = "a5"
DEFAULT_BOOKLET_SHEET = "a4"
_MARGIN_REF_SIZE = "a5"

_MARGINS_A5: dict[str, float] = {"top": 16.0, "bottom": 18.0, "inner": 20.0, "outer": 14.0}
_MARGINS_LARGE: dict[str, float] = {"top": 22.0, "bottom": 24.0, "inner": 28.0, "outer": 20.0}


@dataclass(frozen=True)
class PageSize:
    """Especificación de un tamaño de papel vertical (ancho y alto en mm)."""

    width_mm: float
    height_mm: float
    booklet_sheet: bool = False
    margins: dict[str, float] | None = None
    booklet_margins: dict[str, float] | None = None


# Tabla central de tamaños (única fuente de verdad).
# Para agregar un tamaño nuevo solo hace falta sumarlo aquí.
# Si margins o booklet_margins es None, se calculan proporcionalmente desde A5.
PAGE_SIZES: dict[str, PageSize] = {
    "a4": PageSize(210.0, 297.0, booklet_sheet=True, margins=_MARGINS_LARGE, booklet_margins=_MARGINS_A5),
    "a5": PageSize(148.0, 210.0, booklet_sheet=True, margins=_MARGINS_A5),
    "a6": PageSize(105.0, 148.0),
    "letter": PageSize(215.9, 279.4, booklet_sheet=True, margins=_MARGINS_LARGE, booklet_margins=_MARGINS_A5),
}

# Derivados de la tabla central (no duplicar tamaños fuera de PAGE_SIZES)
PAGE_SIZES_MM: dict[str, tuple[float, float]] = {
    name: (spec.width_mm, spec.height_mm) for name, spec in PAGE_SIZES.items()
}
SHEETS: tuple[str, ...] = tuple(name for name, spec in PAGE_SIZES.items() if spec.booklet_sheet)
FORMATS: tuple[str, ...] = (*PAGE_SIZES, BOOKLET_FORMAT)


def _round_half_mm(value: float) -> float:
    """Redondea una medida en mm al múltiplo de 0,5 mm más cercano."""
    return round(value * 2) / 2


def scale_margins(page_width_mm: float) -> dict[str, float]:
    """Escala los márgenes de A5 según el ancho de página (ancho / ancho_A5), redondeando a 0,5 mm."""
    ref_width = PAGE_SIZES[_MARGIN_REF_SIZE].width_mm
    ratio = page_width_mm / ref_width
    return {side: _round_half_mm(mm * ratio) for side, mm in _MARGINS_A5.items()}


def margins_for(fmt: str, booklet_sheet: str = DEFAULT_BOOKLET_SHEET) -> dict[str, float]:
    """Devuelve los márgenes espejados (top, bottom, inner, outer) en mm para el formato dado."""
    if fmt == BOOKLET_FORMAT:
        spec = PAGE_SIZES[booklet_sheet]
        if spec.booklet_margins is not None:
            return dict(spec.booklet_margins)
        return scale_margins(spec.height_mm / 2)
    spec = PAGE_SIZES[fmt]
    if spec.margins is not None:
        return dict(spec.margins)
    return scale_margins(spec.width_mm)


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    input_dir: Path = Path("input")
    output_dir: Path = Path("output")
    format: str = DEFAULT_FORMAT
    combine: bool = True
    start_on_recto: bool = True
    toc_on_recto: bool = False
    font_family: str = "Georgia, 'Times New Roman', serif"
    font_size: str = "11pt"
    line_height: float = 1.45
    booklet_sheet: str = DEFAULT_BOOKLET_SHEET
    split_long_works: bool = False
    max_pages_per_part: int = 400
    split_enabled: bool = False
    split_volumes: object = None
    split_names: object = None
    renumber_chapters: bool = False

    @property
    def is_booklet(self) -> bool:
        return self.format == BOOKLET_FORMAT

    @property
    def page_size_mm(self) -> tuple[float, float]:
        """Tamaño de la página lógica (ancho, alto) en mm."""
        if self.is_booklet:
            spec = PAGE_SIZES[self.booklet_sheet]
            return (spec.height_mm / 2, spec.width_mm)  # mitad de la hoja apaisada
        spec = PAGE_SIZES[self.format]
        return (spec.width_mm, spec.height_mm)

    @property
    def sheet_size_mm(self) -> tuple[float, float]:
        """Hoja física apaisada (ancho, alto) en mm; solo para folleto."""
        spec = PAGE_SIZES[self.booklet_sheet]
        return (spec.height_mm, spec.width_mm)

    @property
    def margins_mm(self) -> dict[str, float]:
        """Márgenes (top, bottom, inner, outer) según el tamaño de la página."""
        return margins_for(self.format, self.booklet_sheet)

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


def _read_split_option(split: dict, book: dict, key: str, default: object) -> object:
    """Lee una opción movida desde [book] a [split], avisando si sigue en [book]."""
    in_split = key in split
    in_book = key in book
    if in_book:
        if in_split:
            print(
                f"[aviso] book.{key} está deprecado y se movió a la sección [split]; "
                f"se usa el valor de [split]. Actualizá tu config.toml.",
                file=sys.stderr,
            )
        else:
            print(
                f"[aviso] book.{key} está deprecado y se movió a la sección [split]. "
                f"Actualizá tu config.toml.",
                file=sys.stderr,
            )
    if in_split:
        return split[key]
    if in_book:
        return book[key]
    return default


def load_config(path: str | Path = "config.toml") -> Config:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"No existe el archivo de configuración: {path}")
    with path.open("rb") as f:
        data = tomllib.load(f)

    base = path.resolve().parent  # las rutas son relativas al config.toml
    inp = data.get("input", {})
    book = data.get("book", {})
    booklet = data.get("booklet", {})
    split = data.get("split", {})
    if not isinstance(split, dict):
        raise ConfigError("la sección [split] debe ser una tabla TOML")
    defaults = Config()

    split_long_works = bool(
        _read_split_option(split, book, "split_long_works", defaults.split_long_works)
    )
    max_pages_per_part = int(
        _read_split_option(split, book, "max_pages_per_part", defaults.max_pages_per_part)
    )

    raw_volumes = split.get("volumes")
    split_volumes = tuple(raw_volumes) if isinstance(raw_volumes, list) else raw_volumes
    raw_names = split.get("names")
    split_names = tuple(raw_names) if isinstance(raw_names, list) else raw_names

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
        split_long_works=split_long_works,
        max_pages_per_part=max_pages_per_part,
        split_enabled=bool(split.get("enabled", defaults.split_enabled)),
        split_volumes=split_volumes,
        split_names=split_names,
        renumber_chapters=bool(split.get("renumber_chapters", defaults.renumber_chapters)),
    )
    return _validate(cfg)
