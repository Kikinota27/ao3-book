import re
import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader

from src.ao3book.__main__ import main, parse_args, run
from src.ao3book.booklet import MM_TO_PT, booklet_order, impose_booklet
from src.ao3book.build import STYLES_DIR, build_css, build_documents
from src.ao3book.config import (
    BOOKLET_FORMAT,
    FORMATS,
    PAGE_SIZES,
    SHEETS,
    Config,
    ConfigError,
    load_config,
    margins_for,
    scale_margins,
)
from src.ao3book.model import Chapter, Work
from src.ao3book.parser import parse_work
from src.ao3book.render import render_pdf
from src.ao3book.split import measure_chapters, split_works

MULTI_FIXTURE = Path(__file__).parent / "fixtures" / "multi_chapter_sample.html"

# Excepciones documentadas de unidades absolutas permitidas en book.css (actualmente ninguna:
# tamaño de página y márgenes viven en Config.page_css()).
ALLOWED_FIXED_CSS_UNITS: set[str] = set()

_LOREM = (
    "<p>En un lugar de la Mancha, de cuyo nombre no quiero acordarme, no ha mucho tiempo "
    "que vivía un hidalgo de los de lanza en astillero, adarga antigua, rocín flaco y galgo "
    "corredor. Una olla de algo más vaca que carnero, salpicón las más noches, duelos y "
    "quebrantos los sábados, lantejas los viernes, algún palomino de añadidura los domingos, "
    "consumían las tres partes de su hacienda.</p>"
)


def _make_long_work(n_chapters: int = 3, paras_per_chapter: int = 10) -> Work:
    return Work(
        title="Obra de Prueba",
        author="Autora",
        summary_html="<p>Resumen breve de la obra de prueba.</p>",
        chapters=[
            Chapter(i, f"Chapter {i}", _LOREM * paras_per_chapter)
            for i in range(1, n_chapters + 1)
        ],
    )


# ---------- Tabla central de tamaños y @page ----------


def test_size_table_derives_formats_and_sheets():
    assert tuple(PAGE_SIZES.keys()) == ("a4", "a5", "a6", "letter")
    assert SHEETS == ("a4", "a5", "letter")
    assert FORMATS == (*PAGE_SIZES, BOOKLET_FORMAT)
    assert "a6" not in SHEETS


@pytest.mark.parametrize(
    "fmt, sheet, expected_size",
    [
        ("a4", "a4", "210mm 297mm"),
        ("a5", "a4", "148mm 210mm"),
        ("a6", "a4", "105mm 148mm"),
        ("letter", "a4", "215.9mm 279.4mm"),
        ("booklet", "a4", "148.5mm 210mm"),
        ("booklet", "a5", "105mm 148mm"),
        ("booklet", "letter", "139.7mm 215.9mm"),
    ],
)
def test_page_css_dimensions_from_size_table(fmt, sheet, expected_size):
    css = Config(format=fmt, booklet_sheet=sheet).page_css()
    assert f"size: {expected_size};" in css


# ---------- Márgenes ----------


@pytest.mark.parametrize(
    "fmt, sheet, expected",
    [
        # Formatos existentes: exactamente los valores históricos (cero regresión)
        ("a4", "a4", {"top": 22.0, "bottom": 24.0, "inner": 28.0, "outer": 20.0}),
        ("letter", "a4", {"top": 22.0, "bottom": 24.0, "inner": 28.0, "outer": 20.0}),
        ("a5", "a4", {"top": 16.0, "bottom": 18.0, "inner": 20.0, "outer": 14.0}),
        ("booklet", "a4", {"top": 16.0, "bottom": 18.0, "inner": 20.0, "outer": 14.0}),
        ("booklet", "letter", {"top": 16.0, "bottom": 18.0, "inner": 20.0, "outer": 14.0}),
        # Tamaños nuevos: A5 escalado por (105 / 148), redondeado a 0,5 mm:
        #   top    = 16 * 105 / 148 = 11.351 -> 11.5
        #   bottom = 18 * 105 / 148 = 12.770 -> 13.0
        #   inner  = 20 * 105 / 148 = 14.189 -> 14.0
        #   outer  = 14 * 105 / 148 =  9.932 -> 10.0
        ("a6", "a4", {"top": 11.5, "bottom": 13.0, "inner": 14.0, "outer": 10.0}),
        ("booklet", "a5", {"top": 11.5, "bottom": 13.0, "inner": 14.0, "outer": 10.0}),
    ],
)
def test_margins_exact_and_proportional(fmt, sheet, expected):
    cfg = Config(format=fmt, booklet_sheet=sheet)
    assert cfg.margins_mm == expected
    assert margins_for(fmt, sheet) == expected

    css = cfg.page_css()
    assert f"margin-top: {expected['top']:g}mm; margin-bottom: {expected['bottom']:g}mm;" in css
    assert f"@page :left {{ margin-left: {expected['outer']:g}mm; margin-right: {expected['inner']:g}mm; }}" in css
    assert f"@page :right {{ margin-left: {expected['inner']:g}mm; margin-right: {expected['outer']:g}mm; }}" in css
    assert expected["inner"] > expected["outer"]


def test_scale_margins_function():
    assert scale_margins(148.0) == {"top": 16.0, "bottom": 18.0, "inner": 20.0, "outer": 14.0}
    assert scale_margins(105.0) == {"top": 11.5, "bottom": 13.0, "inner": 14.0, "outer": 10.0}


# ---------- Validación de errores desde la tabla ----------


def test_invalid_format_lists_all_table_options(tmp_path):
    bad = tmp_path / "bad_fmt.toml"
    bad.write_text('[book]\nformat = "b5"\n', encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_config(bad)
    msg = str(exc.value)
    assert ", ".join(FORMATS) in msg

    with pytest.raises(ConfigError) as exc_override:
        Config().with_format("a3")
    assert ", ".join(FORMATS) in str(exc_override.value)


@pytest.mark.parametrize("bad_sheet", ["a6", "b5", "legal"])
def test_invalid_booklet_sheet_lists_all_sheet_options(tmp_path, bad_sheet):
    bad = tmp_path / "bad_sheet.toml"
    bad.write_text(f'[book]\nformat = "booklet"\n[booklet]\nsheet = "{bad_sheet}"\n', encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_config(bad)
    assert ", ".join(SHEETS) in str(exc.value)


# ---------- CLI: --format a6 y --format booklet ----------


def test_cli_accepts_a6_and_booklet_and_runs(tmp_path, capsys):
    assert parse_args(["--format", "a6"]).format == "a6"
    assert parse_args(["--format", "A6"]).format == "a6"
    assert parse_args(["--format", "booklet"]).format == "booklet"

    with pytest.raises(SystemExit):
        parse_args(["--help"])
    help_text = capsys.readouterr().out
    for fmt in FORMATS:
        assert fmt in help_text

    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    shutil.copy(MULTI_FIXTURE, inp / "obra.html")
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        '[input]\ndir = "input"\noutput_dir = "output"\n[book]\ncombine = false\n',
        encoding="utf-8",
    )

    assert main(["--config", str(cfg_file), "--format", "a6"]) == 0
    pdf = out / "cronicas-del-norte.pdf"
    assert pdf.exists()
    page = PdfReader(str(pdf)).pages[0]
    assert abs(float(page.mediabox.width) - 105.0 * MM_TO_PT) < 0.5
    assert abs(float(page.mediabox.height) - 148.0 * MM_TO_PT) < 0.5


# ---------- Folleto con sheet = "a5" ----------


def test_booklet_sheet_a5_dimensions_and_imposition_order(tmp_path):
    cfg = Config(format="booklet", booklet_sheet="a5", combine=False)
    assert cfg.page_size_mm == (105.0, 148.0)
    assert cfg.sheet_size_mm == (210.0, 148.0)

    # 6 páginas numeradas con marcadores únicos para verificar el orden de imposición
    chapters = [
        Chapter(i, f"Chapter {i}", f"<p>MARCA-CAP-{i}</p>")
        for i in range(1, 5)
    ]
    work = Work("Folleto A5", "Autor", "<p>Resumen</p>", chapters)
    doc = build_documents([work], cfg)[0]

    plain = tmp_path / "plain.pdf"
    imposed = tmp_path / "booklet.pdf"
    render_pdf(doc.html, plain)
    impose_booklet(plain, imposed, cfg.sheet_size_mm)

    plain_reader = PdfReader(str(plain))
    n = len(plain_reader.pages)
    assert n == 6  # portada + índice + 4 capítulos

    # Página lógica: 105 × 148 mm
    p0 = plain_reader.pages[0]
    assert abs(float(p0.mediabox.width) - 105.0 * MM_TO_PT) < 0.5
    assert abs(float(p0.mediabox.height) - 148.0 * MM_TO_PT) < 0.5

    # Hoja de salida apaisada: 210 × 148 mm
    imp_reader = PdfReader(str(imposed))
    expected_sides = booklet_order(n)
    assert len(imp_reader.pages) == len(expected_sides) == 4  # 6 -> 8 páginas -> 2 hojas -> 4 caras
    for side in imp_reader.pages:
        assert abs(float(side.mediabox.width) - 210.0 * MM_TO_PT) < 0.5
        assert abs(float(side.mediabox.height) - 148.0 * MM_TO_PT) < 0.5

    # Orden de imposición para 6 páginas (relleno a 8):
    # cara 0: (None, 0=portada), cara 1: (1=índice, None),
    # cara 2: (5=cap4, 2=cap1),  cara 3: (3=cap2, 4=cap3)
    assert expected_sides == [(None, 0), (1, None), (5, 2), (3, 4)]
    assert "Folleto A5" in imp_reader.pages[0].extract_text()
    assert "MARCA-CAP-1" in imp_reader.pages[2].extract_text()
    assert "MARCA-CAP-4" in imp_reader.pages[2].extract_text()
    assert "MARCA-CAP-2" in imp_reader.pages[3].extract_text()
    assert "MARCA-CAP-3" in imp_reader.pages[3].extract_text()


# ---------- Escalado tipográfico ----------


def test_font_size_scales_pages_and_header_footer(tmp_path):
    work = _make_long_work(n_chapters=2, paras_per_chapter=16)

    def render_with(font_size: str) -> PdfReader:
        cfg = Config(format="a5", font_size=font_size, combine=False)
        doc = build_documents([work], cfg)[0]
        pdf = tmp_path / f"obra_{font_size}.pdf"
        render_pdf(doc.html, pdf)
        return PdfReader(str(pdf))

    r11 = render_with("11pt")
    r13 = render_with("13pt")
    assert len(r13.pages) > len(r11.pages)

    # Verificar en una página de cuerpo (con encabezado y pie) que también escalaron
    def tf_sizes(page) -> list[float]:
        stream = page.get_contents().get_data().decode("latin1", errors="ignore")
        return sorted({round(float(m), 2) for m in re.findall(r"/\S+\s+([\d.]+)\s+Tf", stream)})

    # Última página de cada PDF tiene cuerpo + encabezado + número de página
    sizes_11 = tf_sizes(r11.pages[-1])
    sizes_13 = tf_sizes(r13.pages[-1])
    assert len(sizes_11) >= 3 and len(sizes_13) >= 3
    assert sizes_13[0] > sizes_11[0]    # encabezado (@top-center) escaló
    assert sizes_13[1] > sizes_11[1]    # pie (@bottom-left/@bottom-right) escaló
    assert sizes_13[-1] > sizes_11[-1]  # texto base escaló


def test_book_css_has_no_unexpected_fixed_units():
    raw_css = (STYLES_DIR / "book.css").read_text(encoding="utf-8")
    # Quitar comentarios CSS antes de buscar unidades absolutas
    css_no_comments = re.sub(r"/\*.*?\*/", "", raw_css, flags=re.DOTALL)

    offenders: list[tuple[int, str, str]] = []
    unit_re = re.compile(r"\b\d+(?:\.\d+)?(?:pt|px|mm|cm|in|pc|q)\b", re.IGNORECASE)
    for lineno, line in enumerate(css_no_comments.splitlines(), start=1):
        for match in unit_re.finditer(line):
            token = match.group(0).lower()
            if token not in ALLOWED_FIXED_CSS_UNITS:
                offenders.append((lineno, token, line.strip()))

    assert offenders == [], f"Unidades fijas inesperadas en book.css: {offenders}"


# ---------- División automática y manual con format a6 ----------


def test_split_works_and_measure_chapters_with_a6(tmp_path):
    work = _make_long_work(n_chapters=4, paras_per_chapter=6)
    cfg_a5 = Config(format="a5", combine=False)
    cfg_a6 = Config(format="a6", combine=False, split_long_works=True, max_pages_per_part=10)

    measured_a5 = measure_chapters(work, build_css(cfg_a5), render_pdf)
    measured_a6 = measure_chapters(work, build_css(cfg_a6), render_pdf)
    assert measured_a5 is not None and measured_a6 is not None

    front_a5, pages_a5 = measured_a5
    front_a6, pages_a6 = measured_a6
    assert len(pages_a6) == 4
    assert sum(pages_a6) > sum(pages_a5)  # en A6 la misma obra ocupa más páginas que en A5

    # División automática usando A6
    parts = split_works([work], cfg_a6, render=render_pdf)
    assert len(parts) >= 2
    assert [c.number for p in parts for c in p.chapters] == [1, 2, 3, 4]

    # División manual en tomos con A6 de punta a punta
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    shutil.copy(MULTI_FIXTURE, inp / "obra.html")
    cfg_manual = Config(
        input_dir=inp,
        output_dir=out,
        format="a6",
        split_enabled=True,
        split_volumes=("1-3", "4-7"),
        split_names=("Tomo 1", "Tomo 2"),
    )
    assert run(cfg_manual, render_pdf) == 0
    pdfs = sorted(out.glob("*.pdf"))
    assert [p.name for p in pdfs] == [
        "cronicas-del-norte-part-i-tomo-1.pdf",
        "cronicas-del-norte-part-ii-tomo-2.pdf",
    ]
    for pdf in pdfs:
        p0 = PdfReader(str(pdf)).pages[0]
        assert abs(float(p0.mediabox.width) - 105.0 * MM_TO_PT) < 0.5
        assert abs(float(p0.mediabox.height) - 148.0 * MM_TO_PT) < 0.5
