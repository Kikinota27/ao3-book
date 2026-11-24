"""Imposición para folleto: reordena las páginas de un PDF en hojas apaisadas.

Cada hoja lleva 2 páginas por cara (4 páginas lógicas por hoja física). El orden
es el de cuadernillo, de modo que al imprimir a doble cara (voltear por el borde
corto), plegar y encuadernar, la lectura queda en orden. Opcionalmente divide el
libro en varios cuadernillos consecutivos (signatures) dentro del mismo PDF.
"""
from __future__ import annotations

from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter, Transformation

MM_TO_PT = 72 / 25.4


def booklet_order(n_pages: int, start: int = 0) -> list[tuple[int | None, int | None]]:
    """Devuelve, para cada cara de hoja, el par (izquierda, derecha) de páginas.

    Impone `n_pages` páginas consecutivas empezando en el índice `start` (0-based).
    Si `n_pages` no es múltiplo de 4, las páginas faltantes al final se devuelven
    como None (página en blanco).
    """
    if n_pages <= 0:
        return []
    total = -(-n_pages // 4) * 4  # redondeo hacia arriba al múltiplo de 4

    def page(i: int) -> int | None:
        return start + i if i < n_pages else None

    sides = []
    for s in range(total // 4):
        sides.append((page(total - 1 - 2 * s), page(2 * s)))          # frente
        sides.append((page(2 * s + 1), page(total - 2 - 2 * s)))      # dorso
    return sides


def signature_sheets(
    n_pages: int,
    sheets_per_signature: int | None = None,
    balance: bool = False,
) -> list[int]:
    """Calcula cuántas hojas físicas lleva cada cuadernillo.

    Si `sheets_per_signature` es None, todo el libro va en un único cuadernillo.
    Con `balance=False`, llena cuadernillos de `sheets_per_signature` hojas y deja
    el resto en el último. Con `balance=True`, reparte las hojas totales lo más
    parejo posible (diferencia máxima de 1 hoja; los primeros llevan la extra) sin
    superar `sheets_per_signature`.
    """
    if n_pages <= 0:
        return []
    total_sheets = -(-n_pages // 4)
    if sheets_per_signature is None:
        return [total_sheets]
    if isinstance(sheets_per_signature, bool) or not isinstance(sheets_per_signature, int) or sheets_per_signature < 1:
        raise ValueError("sheets_per_signature debe ser un número entero mayor o igual que 1")
    if total_sheets <= sheets_per_signature:
        return [total_sheets]
    if balance:
        k = -(-total_sheets // sheets_per_signature)
        base, extra = divmod(total_sheets, k)
        return [base + 1] * extra + [base] * (k - extra)
    full, rem = divmod(total_sheets, sheets_per_signature)
    return [sheets_per_signature] * full + ([rem] if rem else [])


def signature_order(
    n_pages: int,
    sheets_per_signature: int | None = None,
    balance: bool = False,
) -> list[tuple[int | None, int | None]]:
    """Devuelve los pares (izquierda, derecha) de todas las caras del folleto.

    Aplica `booklet_order` a cada cuadernillo por separado en orden consecutivo.
    Las páginas en blanco de relleno quedan siempre solo al final del libro (en el
    último cuadernillo).
    """
    sides: list[tuple[int | None, int | None]] = []
    offset = 0
    for sheets in signature_sheets(n_pages, sheets_per_signature, balance=balance):
        chunk = min(sheets * 4, n_pages - offset)
        sides.extend(booklet_order(chunk, start=offset))
        offset += chunk
    return sides


def _sheets_label(n: int) -> str:
    return f"{n} hoja" if n == 1 else f"{n} hojas"


def format_signatures_message(n_pages: int, sheets: list[int], balance: bool = False) -> str:
    """Arma el mensaje por consola con el detalle de cuadernillos y pasos de armado."""
    sizes = " + ".join(str(s) for s in sheets)
    if len(set(sheets)) == 1:
        size = sheets[0]
        if balance and len(sheets) == 2 and size > 1:
            sep = f"separá el montón a las {size} hojas"
        else:
            sep = f"separá el montón cada {_sheets_label(size)}"
    elif not balance:
        sep = f"separá el montón cada {_sheets_label(sheets[0])} (el último cuadernillo tiene {sheets[-1]})"
    else:
        groups = ", ".join(str(s) for s in sheets[:-1]) + f" y {sheets[-1]}"
        sep = f"separá el montón en grupos de {groups} hojas"

    return (
        f"Folleto: {n_pages} páginas → {len(sheets)} cuadernillos ({sizes} hojas). "
        f"Imprimí a doble cara, voltear por el borde corto, y {sep}. "
        f"Cosé o pegá cada cuadernillo por su pliegue y luego uní los cuadernillos en orden."
    )


def _place(sheet: PageObject, page: PageObject, cell_x: float, cell_w: float, cell_h: float) -> None:
    """Coloca una página dentro de una mitad de la hoja, centrada y a escala."""
    pw, ph = float(page.mediabox.width), float(page.mediabox.height)
    scale = min(cell_w / pw, cell_h / ph)
    tx = cell_x + (cell_w - pw * scale) / 2
    ty = (cell_h - ph * scale) / 2
    sheet.merge_transformed_page(page, Transformation().scale(scale).translate(tx, ty))


def impose_booklet(
    src: str | Path,
    dst: str | Path,
    sheet_size_mm: tuple[float, float],
    *,
    signatures: bool = False,
    sheets_per_signature: int = 50,
    balance: bool = False,
) -> Path:
    """Genera en `dst` la versión impuesta de `src`.

    sheet_size_mm: hoja física apaisada (ancho, alto) en mm.
    """
    reader = PdfReader(str(src))
    n = len(reader.pages)
    if n == 0:
        raise ValueError(f"El PDF está vacío: {src}")

    sheet_w, sheet_h = (v * MM_TO_PT for v in sheet_size_mm)
    cell_w = sheet_w / 2

    per_sig = sheets_per_signature if signatures else None
    writer = PdfWriter()
    for left, right in signature_order(n, per_sig, balance=balance):
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
