"""Imposición para folleto: reordena las páginas de un PDF en hojas apaisadas.

Cada hoja lleva 2 páginas por cara. El orden es el de cuadernillo, de modo que
al imprimir a doble cara (voltear por el borde corto), plegar y encuadernar, la
lectura queda en orden.
"""
from __future__ import annotations

from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter, Transformation

MM_TO_PT = 72 / 25.4


def booklet_order(n_pages: int) -> list[tuple[int | None, int | None]]:
    """Devuelve, para cada cara de hoja, el par (izquierda, derecha) de páginas.

    Los índices empiezan en 0. Si n_pages no es múltiplo de 4, las páginas que
    sobran se devuelven como None (página en blanco).
    """
    total = -(-n_pages // 4) * 4  # redondeo hacia arriba al múltiplo de 4

    def page(i: int) -> int | None:
        return i if i < n_pages else None

    sides = []
    for s in range(total // 4):
        sides.append((page(total - 1 - 2 * s), page(2 * s)))          # frente
        sides.append((page(2 * s + 1), page(total - 2 - 2 * s)))      # dorso
    return sides


def _place(sheet: PageObject, page: PageObject, cell_x: float, cell_w: float, cell_h: float) -> None:
    """Coloca una página dentro de una mitad de la hoja, centrada y a escala."""
    pw, ph = float(page.mediabox.width), float(page.mediabox.height)
    scale = min(cell_w / pw, cell_h / ph)
    tx = cell_x + (cell_w - pw * scale) / 2
    ty = (cell_h - ph * scale) / 2
    sheet.merge_transformed_page(page, Transformation().scale(scale).translate(tx, ty))


def impose_booklet(src: str | Path, dst: str | Path, sheet_size_mm: tuple[float, float]) -> Path:
    """Genera en `dst` la versión impuesta de `src`.

    sheet_size_mm: hoja física apaisada (ancho, alto) en mm, p. ej. (297, 210).
    """
    reader = PdfReader(str(src))
    n = len(reader.pages)
    if n == 0:
        raise ValueError(f"El PDF está vacío: {src}")

    sheet_w, sheet_h = (v * MM_TO_PT for v in sheet_size_mm)
    cell_w = sheet_w / 2

    writer = PdfWriter()
    for left, right in booklet_order(n):
        sheet = PageObject.create_blank_page(width=sheet_w, height=sheet_h)
        if left is not None:
            _place(sheet, reader.pages[left], 0, cell_w, sheet_h)
        if right is not None:
            _place(sheet, reader.pages[right], cell_w, cell_w, sheet_h)
        writer.add_page(sheet)

    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("wb") as f:
        writer.write(f)
    return dst
