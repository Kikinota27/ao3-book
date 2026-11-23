"""Divide obras muy largas en partes, sin cortar capítulos.

Mide cuántas páginas ocupa cada capítulo (renderizando la obra) y agrupa
capítulos consecutivos hasta llenar el límite de páginas por parte.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Callable

from pypdf import PdfReader

from .build import build_css, render_html
from .config import Config
from .model import Work
from .render import render_pdf

_ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def to_roman(n: int) -> str:
    out = ""
    for value, symbol in _ROMAN:
        while n >= value:
            out += symbol
            n -= value
    return out


def _greedy(front: int, pages: list[int], limit: int) -> list[list[int]]:
    """Llena cada parte hasta el límite; la última puede quedar corta."""
    groups: list[list[int]] = [[]]
    used = front
    for index, count in enumerate(pages):
        if groups[-1] and used + count > limit:  # no cabe: abrir parte nueva
            groups.append([])
            used = front
        groups[-1].append(index)
        used += count
    return groups


def _balanced(front: int, pages: list[int], limit: int, k: int) -> list[list[int]] | None:
    """Reparte en k partes de tamaño parecido. Devuelve None si necesitaría más de k."""
    # suffix[i] = páginas de los capítulos i..fin
    suffix = [0] * (len(pages) + 1)
    for i in range(len(pages) - 1, -1, -1):
        suffix[i] = suffix[i + 1] + pages[i]

    groups: list[list[int]] = [[]]
    used = front
    start = 0  # primer capítulo de la parte abierta
    for i, count in enumerate(pages):
        parts_left = max(k - len(groups) + 1, 1)
        target = (suffix[start] + parts_left * front) / parts_left
        # cerrar si no entra, o si agregarlo la aleja del tamaño objetivo
        if groups[-1] and (used + count > limit or abs(used + count - target) > abs(used - target)):
            groups.append([])
            used = front
            start = i
        groups[-1].append(i)
        used += count
    return groups if len(groups) <= k else None


def group_chapters(front: int, pages: list[int], limit: int) -> list[list[int]]:
    """Agrupa índices de capítulos consecutivos en partes de a lo sumo `limit` páginas
    (salvo un capítulo solo que lo supere), con tamaños parejos.
    `front` = páginas de portada + resumen + índice que se repiten en cada parte."""
    greedy = _greedy(front, pages, limit)
    if len(greedy) == 1:
        return greedy
    return _balanced(front, pages, limit, len(greedy)) or greedy


def measure_chapters(
    work: Work,
    css: str,
    render: Callable[..., object],
    toc_on_recto: bool = False,
) -> tuple[int, list[int]] | None:
    """Devuelve (páginas previas al primer capítulo, páginas de cada capítulo) o None si no se pudo medir."""
    html = render_html([work], css, work.title, start_on_recto=False, toc_on_recto=toc_on_recto)
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "medicion.pdf"
        render(html, pdf)
        reader = PdfReader(str(pdf))
        total = len(reader.pages)
        dests = reader.named_destinations
        try:
            starts = [reader.get_destination_page_number(dests[f"w1-c{c.number}"]) for c in work.chapters]
        except KeyError:
            return None
    ends = starts[1:] + [total]
    return starts[0], [end - start for start, end in zip(starts, ends)]


def split_work(work: Work, config: Config, css: str, render: Callable[..., object] = render_pdf) -> list[Work]:
    if len(work.chapters) < 2:
        return [work]
    measured = measure_chapters(work, css, render, toc_on_recto=config.toc_on_recto)
    if measured is None:
        print(f"[aviso] {work.title}: no se pudo medir los capítulos; no se divide", file=sys.stderr)
        return [work]
    front, pages = measured
    limit = config.max_pages_per_part
    if front + sum(pages) <= limit:
        return [work]

    groups = group_chapters(front, pages, limit)
    for group in groups:
        if front + sum(pages[i] for i in group) > limit:
            print(f"[aviso] {work.title}: un capítulo supera {limit} páginas y no se puede partir",
                  file=sys.stderr)
            break
    if len(groups) == 1:
        return [work]

    return [
        Work(
            title=f"{work.title} Part {to_roman(n)}",
            author=work.author,
            summary_html=work.summary_html,
            chapters=[work.chapters[i] for i in group],
            source=work.source,
            base_title=work.title,
            part=n,
            is_part=True,
        )
        for n, group in enumerate(groups, start=1)
    ]


def split_works(works: list[Work], config: Config, render: Callable[..., object] = render_pdf) -> list[Work]:
    css = build_css(config)
    result: list[Work] = []
    for work in works:
        try:
            parts = split_work(work, config, css, render)
        except RuntimeError:
            raise  # p. ej. WeasyPrint no instalado
        except Exception as error:  # noqa: BLE001 - un fallo no frena el lote
            print(f"[aviso] {work.title}: no se pudo dividir ({error}); se deja completa", file=sys.stderr)
            parts = [work]
        if len(parts) > 1:
            print(f"  {work.title}: dividida en {len(parts)} partes", flush=True)
        result.extend(parts)
    return result