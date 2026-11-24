"""Modelos de datos: una obra y sus capítulos."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Chapter:
    number: int
    title: str   # ya normalizado, p. ej. "Chapter 1" o "Chapter 3: Algo"
    html: str    # contenido limpio del capítulo


@dataclass
class Work:
    title: str
    author: str
    summary_html: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    source: Path | None = None
    base_title: str = ""   # título original si es una parte
    part: int = 0          # 0 = obra completa; 1, 2... = número de parte
    is_part: bool = False
    subtitle: str = ""     # subtítulo opcional del tomo (split.names)

    @property
    def sort_key(self) -> tuple[str, int]:
        return ((self.base_title or self.title).casefold(), self.part)

    @property
    def is_single_chapter(self) -> bool:
        """Obra de capítulo único: sin encabezado de capítulo ni índice.
        Una parte con un solo capítulo conserva su encabezado."""
        return len(self.chapters) == 1 and not self.is_part

    @property
    def show_toc(self) -> bool:
        return len(self.chapters) > 1 or self.is_part