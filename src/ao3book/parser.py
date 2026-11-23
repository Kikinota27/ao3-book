"""Parser de descargas HTML de AO3: archivo .html -> Work.

Solo extrae título, autor, resumen y capítulos. Tags, stats, notas y
afterword se descartan. No sabe nada de estilos ni de formato de salida.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from .model import Chapter, Work

# Etiquetas que se conservan en el texto; el resto se "desenvuelve" (se queda
# su contenido, se pierde la etiqueta). Sin atributos, salvo p centrado.
ALLOWED = {
    "p", "em", "strong", "i", "b", "u", "s", "strike", "del", "sub", "sup",
    "blockquote", "hr", "br", "ul", "ol", "li", "h3", "h4", "h5", "h6",
}
DROP = ["script", "style", "img", "svg", "iframe", "object", "audio", "video", "noscript"]

# "Chapter 3: Chapter 3" (capítulo sin título real) -> "Chapter 3"
_DUPLICATED = re.compile(r"^chapter\s+(\d+)\s*:\s*chapter\s+\1$", re.IGNORECASE)
_CENTER = re.compile(r"text-align:\s*center", re.IGNORECASE)


def normalize_chapter_title(raw: str, number: int) -> str:
    """Limpia el título de un capítulo según las reglas del proyecto."""
    title = " ".join(raw.split())
    if not title:
        return f"Chapter {number}"
    match = _DUPLICATED.match(title)
    if match:
        return f"Chapter {match.group(1)}"
    return title


def _clean_html(element: Tag) -> str:
    """Devuelve el HTML interno de un elemento, sin links ni atributos."""
    el = BeautifulSoup(str(element), "lxml").find(element.name)  # copia independiente
    for tag in el.find_all(DROP):
        tag.extract()
    for tag in el.find_all(True):
        if tag.name not in ALLOWED:
            tag.unwrap()
            continue
        centered = tag.name == "p" and (
            str(tag.get("align", "")).lower() == "center"
            or _CENTER.search(str(tag.get("style", "")))
        )
        tag.attrs = {"class": "center"} if centered else {}
    for p in el.find_all("p"):
        if not p.get_text(strip=True) and not p.find("hr"):
            p.extract()
    return "".join(str(child) for child in el.contents).strip()


def _extract_chapters(root: Tag) -> list[Chapter]:
    """Recorre #chapters: meta.group (título) + userstuff (texto) por capítulo."""
    chapters: list[Chapter] = []
    pending_title = ""
    for child in root.find_all(recursive=False):
        classes = child.get("class", [])
        if child.name != "div":
            continue
        if "meta" in classes and "group" in classes:
            heading = child.find("h2")
            pending_title = heading.get_text() if heading else ""
        elif "userstuff" in classes:
            number = len(chapters) + 1
            chapters.append(
                Chapter(number, normalize_chapter_title(pending_title, number), _clean_html(child))
            )
            pending_title = ""
        # los div.meta sueltos son notas finales del capítulo: se ignoran

    if chapters:
        return chapters

    # Obra de capítulo único: el texto está directo dentro de #chapters
    for meta in root.find_all("div", class_="meta"):
        meta.extract()
    html = _clean_html(root)
    return [Chapter(1, "Chapter 1", html)] if html else []


def _text(element: Tag | None) -> str:
    return " ".join(element.get_text().split()) if element else ""


def parse_work(path: str | Path) -> Work:
    """Parsea un archivo HTML de AO3 y devuelve la obra."""
    path = Path(path)
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"), "lxml")

    root = soup.find(id="chapters")
    if root is None:
        raise ValueError("no parece una descarga de AO3 (falta #chapters)")

    preface = soup.find(id="preface")
    meta = preface.find("div", class_="meta") if preface else None

    # Título: h1; si falta, lo que viene antes del primer " - " en <title>
    title = _text(meta.find("h1")) if meta else ""
    if not title and soup.title and soup.title.string:
        title = soup.title.string.split(" - ")[0].strip()
    title = title or path.stem

    # Autor: byline sin el prefijo "by "
    author = _text(meta.find(class_="byline")) if meta else ""
    author = re.sub(r"^by\s+", "", author, flags=re.IGNORECASE)

    # Resumen: el blockquote que sigue al <p>Summary</p>
    summary_html = ""
    if meta:
        label = meta.find("p", string=lambda s: s and s.strip() == "Summary")
        quote = label.find_next_sibling("blockquote") if label else None
        if quote:
            summary_html = _clean_html(quote)

    chapters = _extract_chapters(root)
    if not chapters:
        raise ValueError("no se encontró texto de capítulos")

    return Work(title=title, author=author, summary_html=summary_html,
                chapters=chapters, source=path)


def list_html_files(directory: str | Path) -> list[Path]:
    """Devuelve los archivos .html/.htm de una carpeta, ordenados por nombre."""
    return sorted(
        p for p in Path(directory).iterdir()
        if p.is_file() and p.suffix.lower() in {".html", ".htm"}
    )


def parse_dir(directory: str | Path) -> list[Work]:
    """Parsea todos los .html de una carpeta. Un archivo roto no frena el lote."""
    works: list[Work] = []
    for path in list_html_files(directory):
        try:
            works.append(parse_work(path))
        except Exception as error:  # noqa: BLE001 - se informa y se sigue
            print(f"[aviso] {path.name}: {error}", file=sys.stderr)
    return works
