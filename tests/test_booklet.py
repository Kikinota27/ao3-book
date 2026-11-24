"""Tests del modo folleto por cuadernillos (signatures), sin fixtures reales."""
from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from src.ao3book.__main__ import run
from src.ao3book.booklet import (
    MM_TO_PT,
    booklet_order,
    format_signatures_message,
    impose_booklet,
    signature_order,
    signature_sheets,
)
from src.ao3book.config import Config, ConfigError, load_config


def _make_numbered_pdf(path: Path, n_pages: int, width: float = 419.5, height: float = 595.3) -> Path:
    """Crea un PDF sintético de `n_pages` páginas marcadas como P0, P1, ... con pypdf."""
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)

    for i in range(n_pages):
        page = writer.add_blank_page(width=width, height=height)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 40 500 Td (PAGE-{i}) Tj ET".encode("ascii"))
        page[NameObject("/Contents")] = writer._add_object(stream)

    with path.open("wb") as f:
        writer.write(f)
    return path


def _fake_render(pages: int):
    """Reemplaza a WeasyPrint generando un PDF sintético de `pages` páginas."""

    def render(html: str, out_path: str | Path, base_url=None) -> Path:
        render.calls.append((html, Path(out_path)))
        return _make_numbered_pdf(Path(out_path), pages)

    render.calls = []
    return render


def _write_synthetic_ao3_html(path: Path, title: str = "Obra Sintética", n_chapters: int = 4) -> Path:
    chapters = "".join(
        f'<div class="meta group"><h2 class="heading">Chapter {i}</h2></div>'
        f'<div class="userstuff"><p>Texto del capítulo {i}.</p></div>'
        for i in range(1, n_chapters + 1)
    )
    html = (
        f'<html><body><div id="preface"><div class="meta"><h1>{title}</h1>'
        f'<div class="byline">by Autora</div>'
        f'<p>Summary</p><blockquote class="userstuff"><p>Resumen.</p></blockquote>'
        f'</div></div><div id="chapters">{chapters}</div></body></html>'
    )
    path.write_text(html, encoding="utf-8")
    return path


# ---------- Particionado en cuadernillos ----------


def test_signature_sheets_unbalanced_230_pages_50_sheets():
    # 230 págs = 58 hojas -> 50 hojas (200 págs) + 8 hojas (30 págs + 2 en blanco)
    assert signature_sheets(230, 50, balance=False) == [50, 8]
    sides = signature_order(230, 50, balance=False)
    assert len(sides) == 58 * 2  # 116 caras en el PDF

    sig1_pages = [p for pair in sides[:100] for p in pair]
    sig2_pages = [p for pair in sides[100:] for p in pair]
    assert sorted(sig1_pages) == list(range(200))
    assert sig2_pages.count(None) == 2
    assert sorted(p for p in sig2_pages if p is not None) == list(range(200, 230))


def test_signature_sheets_exact_fit_single_signature():
    # 200 págs con N=50 -> 1 único cuadernillo de 50 hojas, idéntico al modo sin cuadernillos
    assert signature_sheets(200, 50, balance=False) == [50]
    assert signature_sheets(200, 50, balance=True) == [50]
    assert signature_order(200, 50, balance=False) == booklet_order(200)
    assert signature_order(200, 50, balance=True) == booklet_order(200)


def test_signature_sheets_balanced_230_pages_50_sheets():
    # 230 págs -> S=58, k=2 -> 29 + 29 hojas
    assert signature_sheets(230, 50, balance=True) == [29, 29]
    sides = signature_order(230, 50, balance=True)
    assert len(sides) == 58 * 2

    sig1_pages = [p for pair in sides[: 29 * 2] for p in pair]
    sig2_pages = [p for pair in sides[29 * 2 :] for p in pair]
    assert None not in sig1_pages
    assert sorted(sig1_pages) == list(range(116))
    assert sig2_pages.count(None) == 2
    assert sorted(p for p in sig2_pages if p is not None) == list(range(116, 230))


def test_signature_sheets_balanced_inexact_distribution():
    # 410 págs -> S=103, N=50 -> k=3 -> 35 + 34 + 34 (los primeros llevan la hoja extra)
    assert signature_sheets(410, 50, balance=True) == [35, 34, 34]
    # 425 págs -> S=107, N=50 -> k=3 -> 36 + 36 + 35
    assert signature_sheets(425, 50, balance=True) == [36, 36, 35]
    # 234 págs -> S=59, N=50 -> k=2 -> 30 + 29
    assert signature_sheets(234, 50, balance=True) == [30, 29]

    # Propiedades generales para distintos tamaños
    for n_pages in (5, 13, 41, 101, 230, 234, 410, 425, 503):
        for n_sheets in (1, 2, 7, 15, 50):
            dist = signature_sheets(n_pages, n_sheets, balance=True)
            total_sheets = -(-n_pages // 4)
            assert sum(dist) == total_sheets
            assert max(dist) <= n_sheets
            assert max(dist) - min(dist) <= 1
            assert dist == sorted(dist, reverse=True)  # los primeros llevan la hoja extra


@pytest.mark.parametrize("n_pages", [1, 2, 3, 4])
def test_short_book_behaves_as_single_signature(n_pages):
    assert signature_sheets(n_pages, 50, balance=False) == [1]
    assert signature_sheets(n_pages, 50, balance=True) == [1]
    assert signature_sheets(n_pages, 1, balance=False) == [1]
    assert signature_order(n_pages, 50, balance=False) == booklet_order(n_pages)


def test_signatures_disabled_ignores_balance():
    assert signature_sheets(230, None, balance=True) == [58]
    assert signature_order(230, None, balance=True) == booklet_order(230)


# ---------- Orden de imposición y posición de páginas en blanco ----------


def test_imposition_order_8_page_signature_and_multi_signature():
    # Un cuadernillo de 8 páginas (2 hojas = 4 caras):
    # hoja 1 frente: (7, 0), dorso: (1, 6); hoja 2 frente: (5, 2), dorso: (3, 4)
    expected_8 = [(7, 0), (1, 6), (5, 2), (3, 4)]
    assert booklet_order(8) == expected_8
    assert signature_order(8, 2, balance=False) == expected_8

    # 14 páginas con N=2 hojas (8 págs por cuadernillo):
    # cuadernillo 1 (págs 0..7): [(7, 0), (1, 6), (5, 2), (3, 4)]
    # cuadernillo 2 (págs 8..13 + 2 en blanco):
    #   hoja 1 frente: (None, 8), dorso: (9, None)
    #   hoja 2 frente: (13, 10),  dorso: (11, 12)
    expected_14 = expected_8 + [(None, 8), (9, None), (13, 10), (11, 12)]
    assert signature_order(14, 2, balance=False) == expected_14


@pytest.mark.parametrize("balance", [False, True])
@pytest.mark.parametrize("n_pages", [5, 6, 7, 9, 10, 11, 14, 17, 23, 31, 230, 234, 410])
def test_blank_padding_pages_appear_only_in_last_signature(n_pages, balance):
    for n_sheets in (1, 2, 5, 50):
        sheets = signature_sheets(n_pages, n_sheets, balance=balance)
        sides = signature_order(n_pages, n_sheets, balance=balance)
        expected_blanks = (-(-n_pages // 4) * 4) - n_pages

        # Todas las caras anteriores al último cuadernillo deben tener 0 blancos
        sides_before_last = sum(sheets[:-1]) * 2
        earlier_pages = [p for pair in sides[:sides_before_last] for p in pair]
        last_pages = [p for pair in sides[sides_before_last:] for p in pair]

        assert None not in earlier_pages
        assert last_pages.count(None) == expected_blanks

        # Todas las páginas reales 0..n_pages-1 aparecen exactamente una vez
        all_real = [p for pair in sides for p in pair if p is not None]
        assert sorted(all_real) == list(range(n_pages))


def test_impose_booklet_synthetic_pdf_with_signatures(tmp_path):
    src = _make_numbered_pdf(tmp_path / "src.pdf", 14)
    dst = tmp_path / "out.pdf"
    sheet_mm = (297.0, 210.0)  # A4 apaisada

    impose_booklet(src, dst, sheet_mm, signatures=True, sheets_per_signature=2, balance=False)

    reader = PdfReader(str(dst))
    assert len(reader.pages) == 8  # 2 cuadernillos de 2 hojas = 4 hojas = 8 caras
    for side in reader.pages:
        assert abs(float(side.mediabox.width) - 297.0 * MM_TO_PT) < 0.5
        assert abs(float(side.mediabox.height) - 210.0 * MM_TO_PT) < 0.5

    # Verificar contenido exacto de cada cara en ambos cuadernillos
    expected_texts = [
        {"PAGE-7", "PAGE-0"},   # cuad. 1, hoja 1 frente
        {"PAGE-1", "PAGE-6"},   # cuad. 1, hoja 1 dorso
        {"PAGE-5", "PAGE-2"},   # cuad. 1, hoja 2 frente
        {"PAGE-3", "PAGE-4"},   # cuad. 1, hoja 2 dorso
        {"PAGE-8"},             # cuad. 2, hoja 1 frente (izquierda en blanco)
        {"PAGE-9"},             # cuad. 2, hoja 1 dorso (derecha en blanco)
        {"PAGE-13", "PAGE-10"}, # cuad. 2, hoja 2 frente
        {"PAGE-11", "PAGE-12"}, # cuad. 2, hoja 2 dorso
    ]
    for side, expected in zip(reader.pages, expected_texts):
        tokens = set(side.extract_text().split())
        assert tokens == expected


# ---------- Configuración y validación ----------


def test_config_loads_signature_defaults_and_values(tmp_path):
    minimal = tmp_path / "minimal.toml"
    minimal.write_text('[book]\nformat = "booklet"\n', encoding="utf-8")
    cfg_default = load_config(minimal)
    assert cfg_default.booklet_signatures is False
    assert cfg_default.booklet_sheets_per_signature == 50
    assert cfg_default.booklet_balance is False

    custom = tmp_path / "custom.toml"
    custom.write_text(
        '[book]\nformat = "booklet"\n'
        '[booklet]\nsheet = "a5"\nsignatures = true\nsheets_per_signature = 12\nbalance = true\n',
        encoding="utf-8",
    )
    cfg = load_config(custom)
    assert cfg.booklet_sheet == "a5"
    assert cfg.booklet_signatures is True
    assert cfg.booklet_sheets_per_signature == 12
    assert cfg.booklet_balance is True


@pytest.mark.parametrize("raw_value", ["0", "-1", "-50", "2.5", '"50"', "true", "false"])
def test_invalid_sheets_per_signature_raises_config_error(tmp_path, raw_value):
    bad = tmp_path / "bad.toml"
    bad.write_text(
        f'[book]\nformat = "booklet"\n[booklet]\nsignatures = true\nsheets_per_signature = {raw_value}\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError) as exc:
        load_config(bad)
    msg = str(exc.value)
    assert "sheets_per_signature" in msg
    assert "entero" in msg and "1" in msg


# ---------- Casos especiales y flujo CLI (run) ----------


@pytest.mark.parametrize("fmt", ["a4", "a5", "a6", "letter"])
def test_signatures_with_non_booklet_format_warns_and_continues(tmp_path, capsys, fmt):
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    _write_synthetic_ao3_html(inp / "obra.html")

    cfg = Config(
        input_dir=inp,
        output_dir=out,
        format=fmt,
        combine=False,
        booklet_signatures=True,
        booklet_sheets_per_signature=10,
        booklet_balance=True,
    )
    assert run(cfg, _fake_render(pages=14)) == 0

    err = capsys.readouterr().err
    assert "[aviso]" in err
    assert 'format = "booklet"' in err

    pdf = out / "obra-sintetica.pdf"
    assert pdf.exists()
    reader = PdfReader(str(pdf))
    assert len(reader.pages) == 14  # sin imponer: conserva las 14 páginas normales
    assert float(reader.pages[0].mediabox.width) < float(reader.pages[0].mediabox.height)


def test_run_booklet_signatures_console_messages(tmp_path, capsys):
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    _write_synthetic_ao3_html(inp / "obra.html")

    # 230 páginas, N=50, balance=False -> 2 cuadernillos (50 + 8 hojas)
    cfg_unbal = Config(
        input_dir=inp,
        output_dir=out,
        format="booklet",
        combine=False,
        booklet_signatures=True,
        booklet_sheets_per_signature=50,
        booklet_balance=False,
    )
    assert run(cfg_unbal, _fake_render(pages=230)) == 0
    stdout = capsys.readouterr().out
    assert "230 páginas → 2 cuadernillos (50 + 8 hojas)" in stdout
    assert "cada 50 hojas (el último cuadernillo tiene 8)" in stdout
    assert "voltear por el borde corto" in stdout
    assert len(PdfReader(str(out / "obra-sintetica.pdf")).pages) == 58 * 2

    # 230 páginas, N=50, balance=True -> 2 cuadernillos (29 + 29 hojas)
    cfg_bal = Config(
        input_dir=inp,
        output_dir=out,
        format="booklet",
        combine=False,
        booklet_signatures=True,
        booklet_sheets_per_signature=50,
        booklet_balance=True,
    )
    assert run(cfg_bal, _fake_render(pages=230)) == 0
    stdout = capsys.readouterr().out
    assert "230 páginas → 2 cuadernillos (29 + 29 hojas)" in stdout
    assert "a las 29 hojas" in stdout

    # Un solo cuadernillo (100 páginas, N=50) -> mantiene el mensaje clásico
    assert run(cfg_unbal, _fake_render(pages=100)) == 0
    stdout = capsys.readouterr().out
    assert "100 páginas -> 25 hojas a doble cara" in stdout
    assert "cuadernillos" not in stdout


def test_format_signatures_message_balanced_unequal():
    msg = format_signatures_message(410, [35, 34, 34], balance=True)
    assert "410 páginas → 3 cuadernillos (35 + 34 + 34 hojas)" in msg
    assert "en grupos de 35, 34 y 34 hojas" in msg


def test_run_booklet_signatures_per_split_volume(tmp_path, capsys):
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    _write_synthetic_ao3_html(inp / "obra.html", n_chapters=4)

    cfg = Config(
        input_dir=inp,
        output_dir=out,
        format="booklet",
        split_enabled=True,
        split_volumes=("1-2", "3-4"),
        booklet_signatures=True,
        booklet_sheets_per_signature=2,
        booklet_balance=False,
    )
    # Cada tomo tiene 14 páginas -> 2 cuadernillos de 2 + 2 hojas -> 8 caras por PDF
    assert run(cfg, _fake_render(pages=14)) == 0
    pdfs = sorted(out.glob("*.pdf"))
    assert len(pdfs) == 2
    for pdf in pdfs:
        assert len(PdfReader(str(pdf)).pages) == 8
    stdout = capsys.readouterr().out
    assert stdout.count("14 páginas → 2 cuadernillos (2 + 2 hojas)") == 2
