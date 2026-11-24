"""Divide obras largas en partes o tomos, sin cortar capítulos.

Soporta dos modos configurados en la sección [split] de config.toml:
- Automático (`split_long_works`): mide cuántas páginas ocupa cada capítulo y
  agrupa capítulos consecutivos hasta llenar el límite de páginas por parte.
- Manual (`enabled`): divide una única obra según rangos de capítulos elegidos
  por el usuario, con validación estricta en dos momentos.
"""
from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path
from typing import Callable, Sequence

from pypdf import PdfReader

from .build import build_css, render_html
from .config import Config
from .model import Chapter, Work
from .render import render_pdf

_ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
          (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]

_RANGE_RE = re.compile(r"^([0-9]+)(?:-([0-9]+))?$")
_CHAPTER_NUM_RE = re.compile(r"^(Chapter)\s+\d+(\s*:.*)?$", re.IGNORECASE)


class SplitValidationError(ValueError):
    """Error fatal en la configuración o cobertura de la división manual ([split])."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


def _format_chapters(start: int, end: int) -> tuple[str, bool]:
    """Devuelve ('el capítulo X', False) o ('los capítulos ...', True)."""
    if start == end:
        return f"el capítulo {start}", False
    if end == start + 1:
        return f"los capítulos {start} y {end}", True
    if end - start <= 3:
        nums = ", ".join(str(n) for n in range(start, end))
        return f"los capítulos {nums} y {end}", True
    return f"los capítulos {start} a {end}", True


def _cap(text: str) -> str:
    return text[0].upper() + text[1:] if text else text


def _renumber_chapters(chapters: list[Chapter]) -> list[Chapter]:
    """Renumera títulos 'Chapter N' o 'Chapter N: ...' desde 1 dentro de un tomo.

    Conserva `chapter.number` intacto para no alterar los anclas internos (`w1-cN`).
    """
    result: list[Chapter] = []
    counter = 1
    for ch in chapters:
        match = _CHAPTER_NUM_RE.match(ch.title)
        if match:
            suffix = match.group(2) or ""
            new_title = f"{match.group(1)} {counter}{suffix}"
            counter += 1
            result.append(Chapter(number=ch.number, title=new_title, html=ch.html))
        else:
            result.append(ch)
    return result


def _build_parts(
    work: Work,
    groups: list[list[int]],
    names: Sequence[str] | None = None,
    renumber: bool = False,
) -> list[Work]:
    """Construye los Work de cada parte/tomo reutilizando la maquinaria común."""
    parts: list[Work] = []
    for n, group in enumerate(groups, start=1):
        chapters = [work.chapters[i] for i in group]
        if renumber:
            chapters = _renumber_chapters(chapters)
        subtitle = names[n - 1].strip() if names else ""
        parts.append(
            Work(
                title=f"{work.title} Part {to_roman(n)}",
                author=work.author,
                summary_html=work.summary_html,
                chapters=chapters,
                source=work.source,
                base_title=work.title,
                part=n,
                is_part=True,
                subtitle=subtitle,
            )
        )
    return parts


def validate_split_config(
    volumes: object,
    names: object = None,
    html_files: Sequence[Path] | None = None,
) -> list[tuple[int, int]]:
    """Momento A: valida [split] y archivos de entrada antes de leer ningún HTML.

    Devuelve la lista de rangos `(inicio, fin)` (1-based, inclusivos) o lanza
    `SplitValidationError` con mensajes detallados en español.
    """
    errors: list[str] = []

    # 1. Exactamente un archivo .html en la carpeta de entrada
    if html_files is not None:
        if len(html_files) == 0:
            errors.append(
                '[error] input.dir: no se encontró ningún archivo .html en la carpeta de entrada. '
                'La división manual ([split] con enabled = true) requiere exactamente un archivo .html '
                'para dividir en tomos. Ejemplo correcto: dejá un único archivo .html en la carpeta '
                'de entrada (p. ej. "input/mi_obra.html").'
            )
        elif len(html_files) > 1:
            preview = ", ".join(p.name for p in html_files[:5])
            if len(html_files) > 5:
                preview += ", ..."
            errors.append(
                f'[error] input.dir: se encontraron {len(html_files)} archivos .html ({preview}), '
                f'pero la división manual ([split] con enabled = true) requiere exactamente uno. '
                f'No se sabe a qué obra aplicar los rangos de split.volumes. '
                f'Ejemplo correcto: dejá un solo archivo .html en la carpeta de entrada o poné '
                f'enabled = false en [split].'
            )

    # 2. volumes debe ser una lista no vacía de strings
    volumes_list: Sequence[object] | None = None
    if volumes is None:
        errors.append(
            '[error] split.volumes: falta definir la lista de tomos cuando split.enabled = true. '
            'Se necesita al menos un rango para dividir la obra. '
            'Ejemplo correcto: volumes = ["1-3", "4-5", "6-8"].'
        )
    elif isinstance(volumes, str):
        errors.append(
            f'[error] split.volumes = "{volumes}": debe ser una lista de textos, no una sola cadena. '
            f'Cada tomo va como un elemento separado entre corchetes. '
            f'Ejemplo correcto: volumes = ["1-3", "4-5", "6-8"].'
        )
    elif not isinstance(volumes, (list, tuple)):
        errors.append(
            f'[error] split.volumes = {volumes!r}: debe ser una lista de textos. '
            f'Cada tomo debe definirse como un rango entre comillas dentro de corchetes. '
            f'Ejemplo correcto: volumes = ["1-3", "4-5", "6-8"].'
        )
    elif len(volumes) == 0:
        errors.append(
            '[error] split.volumes = []: la lista de tomos está vacía. '
            'Con split.enabled = true tenés que definir al menos un tomo. '
            'Ejemplo correcto: volumes = ["1-3", "4-5", "6-8"].'
        )
    else:
        volumes_list = volumes

    # 3-5. Formato, cero y rango invertido por elemento
    parsed: list[tuple[int, int, str, int]] = []
    item_errors = False
    if volumes_list is not None:
        for pos, raw in enumerate(volumes_list, start=1):
            if not isinstance(raw, str):
                item_errors = True
                errors.append(
                    f'[error] split.volumes[{pos}] = {raw!r}: debe ser un texto entre comillas, '
                    f'no {type(raw).__name__}. Cada tomo se escribe como "N" o "N-M". '
                    f'Ejemplo correcto: volumes = ["1-3", "4", "5-8"].'
                )
                continue
            cleaned = raw.strip()
            match = _RANGE_RE.fullmatch(cleaned)
            if not match:
                item_errors = True
                errors.append(
                    f'[error] split.volumes[{pos}] = "{raw}": formato inválido. '
                    f'Cada elemento debe ser un número de capítulo ("N") o un rango ("N-M") '
                    f'usando solo dígitos positivos. Ejemplo correcto: volumes = ["1-3", "4", "5-8"].'
                )
                continue
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) is not None else start
            if start == 0 or end == 0:
                item_errors = True
                errors.append(
                    f'[error] split.volumes[{pos}] = "{raw}": el número de capítulo no puede ser 0. '
                    f'Los capítulos se numeran por su posición en el archivo empezando desde 1. '
                    f'Ejemplo correcto: volumes = ["1-3", "4-6"].'
                )
                continue
            if end < start:
                item_errors = True
                errors.append(
                    f'[error] split.volumes[{pos}] = "{raw}": el rango está invertido '
                    f'({start} es mayor que {end}). El capítulo inicial debe ser menor o igual '
                    f'que el final. Ejemplo correcto: "{end}-{start}".'
                )
                continue
            parsed.append((start, end, raw, pos))

    # 6-8. Orden ascendente, inicio en 1, sin solapes ni saltos
    if volumes_list is not None and not item_errors and parsed:
        first_start, first_end, first_raw, _ = parsed[0]
        if first_start != 1:
            missing_phrase, plural = _format_chapters(1, first_start - 1)
            verb = "quedan" if plural else "queda"
            errors.append(
                f'[error] split.volumes[1] = "{first_raw}": el primer tomo debe empezar en el '
                f'capítulo 1, pero empieza en {first_start} ({missing_phrase} {verb} sin cubrir). '
                f'Todos los capítulos desde el inicio deben pertenecer a un tomo. '
                f'Ejemplo correcto: volumes = ["1-3", "4-6"].'
            )

        prev_start, prev_end, prev_raw = first_start, first_end, first_raw
        covered_end = first_end
        for start, end, raw, pos in parsed[1:]:
            if start < prev_start:
                errors.append(
                    f'[error] split.volumes[{pos}] = "{raw}": los tomos no están en orden ascendente '
                    f'(empieza en {start}, antes que el tomo anterior "{prev_raw}"). '
                    f'Los tomos deben escribirse de menor a mayor. '
                    f'Ejemplo correcto: volumes = ["1-3", "4-5", "6-8"].'
                )
            elif start <= covered_end:
                ov_end = min(covered_end, end)
                ov_phrase, plural = _format_chapters(start, ov_end)
                verb = "aparecen" if plural else "aparece"
                errors.append(
                    f'[error] split.volumes[{pos}] = "{raw}": hay un solapamiento con el tomo anterior '
                    f'("{prev_raw}"). {_cap(ov_phrase)} {verb} en más de un tomo. '
                    f'Cada capítulo debe estar en exactamente un tomo. '
                    f'Ejemplo correcto: volumes = ["1-3", "4-5", "6-8"].'
                )
            elif start > covered_end + 1:
                gap_phrase, plural = _format_chapters(covered_end + 1, start - 1)
                verb = "pertenecen" if plural else "pertenece"
                errors.append(
                    f'[error] split.volumes[{pos}] = "{raw}": hay un salto. '
                    f'{_cap(gap_phrase)} no {verb} a ningún tomo. '
                    f'Cada capítulo debe estar en exactamente un tomo. '
                    f'Ejemplo correcto: ["1-3", "4-5", "6-7"].'
                )
            covered_end = max(covered_end, end)
            prev_start, prev_end, prev_raw = start, end, raw

    # 9. names (opcional): misma cantidad que volumes, todos strings no vacíos
    if names is not None:
        if not isinstance(names, (list, tuple)):
            errors.append(
                f'[error] split.names = {names!r}: debe ser una lista de textos con un nombre '
                f'por tomo (o quitá split.names si no querés subtítulos). '
                f'Ejemplo correcto: names = ["Año 1", "Año 3", "Año 5"].'
            )
        else:
            if volumes_list is not None and len(names) != len(volumes_list):
                errors.append(
                    f'[error] split.names: tiene {len(names)} elemento(s), pero split.volumes tiene '
                    f'{len(volumes_list)}. Debe haber exactamente un nombre por cada tomo '
                    f'(o quitá split.names si no querés subtítulos). '
                    f'Ejemplo correcto: names = ["Año 1", "Año 3", "Año 5"] (misma cantidad que volumes).'
                )
            for pos, name in enumerate(names, start=1):
                if not isinstance(name, str):
                    errors.append(
                        f'[error] split.names[{pos}] = {name!r}: debe ser un texto entre comillas, '
                        f'no {type(name).__name__}. Ejemplo correcto: names = ["Año 1", "Año 2"].'
                    )
                elif not name.strip():
                    errors.append(
                        f'[error] split.names[{pos}] = "{name}": el nombre del tomo está vacío. '
                        f'Cada elemento de split.names debe tener texto (o quitá split.names si no '
                        f'querés subtítulos). Ejemplo correcto: names = ["Año 1", "Año 2"].'
                    )

    if errors:
        raise SplitValidationError(errors)

    return [(start, end) for start, end, _, _ in parsed]


def validate_split_coverage(
    ranges: Sequence[tuple[int, int]],
    work: Work,
    raw_volumes: Sequence[str] | None = None,
) -> None:
    """Momento B: valida que los rangos coincidan con la cantidad real de capítulos."""
    total = len(work.chapters)
    if total < 2:
        raise SplitValidationError([
            f'[error] "{work.title}": la obra tiene un solo capítulo y no se puede dividir en tomos. '
            f'Para generarla completa, desactivá la división manual. '
            f'Ejemplo correcto: en [split], poné enabled = false.'
        ])

    errors: list[str] = []
    for pos, (start, end) in enumerate(ranges, start=1):
        if end > total:
            raw = (
                str(raw_volumes[pos - 1])
                if raw_volumes and pos <= len(raw_volumes)
                else (f"{start}" if start == end else f"{start}-{end}")
            )
            excess_start = max(start, total + 1)
            excess_phrase, plural = _format_chapters(excess_start, end)
            verb = "existen" if plural else "existe"
            mid = total // 2
            example = f'["1-{mid}", "{mid + 1}-{total}"]' if mid >= 1 and mid < total else f'["1-{total}"]'
            errors.append(
                f'[error] split.volumes[{pos}] = "{raw}": el rango supera la cantidad de capítulos de '
                f'"{work.title}" (la obra tiene {total} capítulos; {excess_phrase} no {verb}). '
                f'El último tomo debe terminar exactamente en el capítulo {total}. '
                f'Ejemplo correcto: volumes = {example}.'
            )

    last_pos = len(ranges)
    last_start, last_end = ranges[-1]
    if last_end < total:
        raw = (
            str(raw_volumes[last_pos - 1])
            if raw_volumes and last_pos <= len(raw_volumes)
            else (f"{last_start}" if last_start == last_end else f"{last_start}-{last_end}")
        )
        missing_phrase, plural = _format_chapters(last_end + 1, total)
        verb = "faltan" if plural else "falta"
        next_vol = f"{total}" if last_end + 1 == total else f"{last_end + 1}-{total}"
        errors.append(
            f'[error] split.volumes[{last_pos}] = "{raw}": cobertura incompleta para "{work.title}" '
            f'(la obra tiene {total} capítulos; {verb} cubrir {missing_phrase}). '
            f'Todos los capítulos de la obra deben estar incluidos en algún tomo. '
            f'Ejemplo correcto: extendé el último rango a "{last_start}-{total}" '
            f'o agregá un tomo "{next_vol}".'
        )

    if errors:
        raise SplitValidationError(errors)


def split_work_manual(
    work: Work,
    ranges: Sequence[tuple[int, int]],
    names: Sequence[str] | None = None,
    renumber: bool = False,
    raw_volumes: Sequence[str] | None = None,
) -> list[Work]:
    """Valida cobertura (momento B) y divide la obra en los tomos indicados."""
    validate_split_coverage(ranges, work, raw_volumes=raw_volumes)
    groups = [list(range(start - 1, end)) for start, end in ranges]
    return _build_parts(work, groups, names=names, renumber=renumber)


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

    return _build_parts(work, groups, renumber=config.renumber_chapters)


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