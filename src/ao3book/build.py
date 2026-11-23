
"""Obras -> documentos HTML listos para renderizar.
 
Según config.combine devuelve un único documento con todas las obras, o uno por
obra. No genera PDF (eso lo hace render.py) ni sabe nada de AO3 (eso es parser.py).
"""
from __future__ import annotations
 
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
 
from jinja2 import Environment, FileSystemLoader
 
from .config import Config
from .model import Work
 
_HERE = Path(__file__).parent
TEMPLATES_DIR = _HERE / "templates"
STYLES_DIR = _HERE / "styles"
 
COMBINED_NAME = "libro"
COMBINED_TITLE = "Libro"
 
 
@dataclass
class Document:
    name: str  # nombre de archivo, sin extensión
    html: str
 
 
def slugify(text: str) -> str:
    """Convierte un título en un nombre de archivo seguro (ascii, minúsculas, guiones)."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)[:80].strip("-")
 
 
def build_css(config: Config) -> str:
    """CSS completo: variables de tipografía + @page generado + book.css."""
    variables = "".join(f"  --{name}: {value};\n" for name, value in config.css_vars().items())
    base = (STYLES_DIR / "book.css").read_text(encoding="utf-8")
    return f":root {{\n{variables}}}\n{config.page_css()}\n{base}"
 
 
def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
 
 
def render_html(
    works: list[Work],
    css: str,
    doc_title: str,
    start_on_recto: bool,
    toc_on_recto: bool = False,
) -> str:
    template = _environment().get_template("book.html.j2")
    return template.render(
        works=works,
        css=css,
        doc_title=doc_title,
        start_on_recto=start_on_recto,
        toc_on_recto=toc_on_recto,
    )
 
 
def _unique_names(works: list[Work]) -> list[str]:
    """Un nombre de archivo por obra; si se repite, agrega -2, -3..."""
    names: list[str] = []
    used: set[str] = set()
    for index, work in enumerate(works, start=1):
        base = slugify(work.title) or (slugify(work.source.stem) if work.source else "") or f"obra-{index}"
        name, n = base, 2
        while name in used:
            name, n = f"{base}-{n}", n + 1
        used.add(name)
        names.append(name)
    return names
 
 
def build_documents(works: list[Work], config: Config) -> list[Document]:
    """Arma los documentos HTML a generar. Las obras se ordenan alfabéticamente por título."""
    if not works:
        return []
 
    works = sorted(works, key=lambda w: w.sort_key)
    css = build_css(config)
 
    if config.combine:
        title = works[0].title if len(works) == 1 else COMBINED_TITLE
        return [
            Document(
                COMBINED_NAME,
                render_html(works, css, title, config.start_on_recto, config.toc_on_recto),
            )
        ]
 
    # Un documento por obra: cada uno es un libro aparte, así que no hace falta
    # forzar la página derecha (la primera página ya lo es).
    return [
        Document(
            name,
            render_html([work], css, work.title, start_on_recto=False, toc_on_recto=config.toc_on_recto),
        )
        for name, work in zip(_unique_names(works), works)
    ]
 