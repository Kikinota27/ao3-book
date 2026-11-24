"""Tests de documentación bilingüe (README.md, README.en.md) y config.toml."""
from __future__ import annotations

import re
import tomllib
from collections import Counter
from pathlib import Path

from src.ao3book.config import Config, load_config

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.toml"
README_ES = ROOT / "README.md"
README_EN = ROOT / "README.en.md"

_SECTION_RE = re.compile(r"^\[([A-Za-z0-9_.-]+)\]\s*(?:#.*)?$")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _github_slug(heading: str) -> str:
    """Genera el ancla al estilo GitHub (GFM) para un encabezado Markdown."""
    text = heading.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def _extract_headings(markdown: str) -> list[tuple[int, str]]:
    """Extrae (nivel, texto) de encabezados Markdown ignorando bloques de código cercados."""
    headings: list[tuple[int, str]] = []
    in_fence = False
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _HEADING_RE.match(line)
        if match:
            headings.append((len(match.group(1)), match.group(2)))
    return headings


def _heading_levels(markdown: str) -> Counter[int]:
    """Cuenta encabezados Markdown por nivel ignorando bloques de código cercados."""
    return Counter(level for level, _ in _extract_headings(markdown))


def _section_bodies(text: str) -> dict[str, list[str]]:
    """Separa las líneas de config.toml por sección, sin mezclar el comentario de la siguiente."""
    lines = text.splitlines()
    headers = [
        (idx, match.group(1))
        for idx, line in enumerate(lines)
        if (match := _SECTION_RE.match(line.strip()))
    ]
    bodies: dict[str, list[str]] = {}
    for pos, (start, name) in enumerate(headers):
        end = headers[pos + 1][0] if pos + 1 < len(headers) else len(lines)
        # Quita comentarios pegados inmediatamente arriba del próximo encabezado [seccion]
        if pos + 1 < len(headers):
            while end > start + 1 and lines[end - 1].lstrip().startswith("#"):
                end -= 1
        # Si la primera línea de la sección es el comentario # EN: del propio encabezado, excluirla
        body = lines[start + 1 : end]
        if body and body[0].lstrip().startswith("# EN:"):
            body = body[1:]
        bodies[name] = body
    return bodies


def test_config_toml_loads_and_validates(capsys):
    with CONFIG_PATH.open("rb") as f:
        raw = tomllib.load(f)
    assert {"input", "book", "booklet", "split"}.issubset(raw.keys())

    cfg = load_config(CONFIG_PATH)
    assert isinstance(cfg, Config)
    assert capsys.readouterr().err == ""


def test_config_toml_has_en_comment_per_key_in_each_section():
    text = CONFIG_PATH.read_text(encoding="utf-8")
    raw = tomllib.loads(text)
    bodies = _section_bodies(text)

    for section, table in raw.items():
        if not isinstance(table, dict):
            continue
        assert section in bodies, f"Falta la sección [{section}] al parsear líneas"
        en_lines = [line for line in bodies[section] if line.lstrip().startswith("# EN:")]
        assert len(en_lines) >= len(table), (
            f"La sección [{section}] tiene {len(table)} clave(s) pero solo {len(en_lines)} línea(s) '# EN:'"
        )


def test_readmes_structure_and_cross_links():
    es_text = README_ES.read_text(encoding="utf-8")
    en_text = README_EN.read_text(encoding="utf-8")

    es_first = es_text.splitlines()[0].strip()
    en_first = en_text.splitlines()[0].strip()
    assert es_first == "🇬🇧 [Read this in English](README.en.md)"
    assert en_first == "🇪🇸 [Leer en español](README.md)"

    es_headings = _heading_levels(es_text)
    en_headings = _heading_levels(en_text)
    assert es_headings == en_headings, (
        f"Cantidad de encabezados distinta: README.md={dict(es_headings)} vs README.en.md={dict(en_headings)}"
    )

    for doc_path, text in ((README_ES, es_text), (README_EN, en_text)):
        anchors = {_github_slug(title) for _, title in _extract_headings(text)}
        for target in _LINK_RE.findall(text):
            if target.startswith(("http://", "https://")):
                continue
            if target.startswith("#"):
                assert target[1:] in anchors, f"Ancla rota en {doc_path.name}: {target}"
                continue
            target_file = target.split("#", 1)[0]
            assert (ROOT / target_file).exists(), f"Enlace roto en {doc_path.name}: {target}"
