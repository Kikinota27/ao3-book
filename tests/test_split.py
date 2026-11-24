import shutil
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from pypdf import PdfReader, PdfWriter

from src.ao3book.__main__ import run
from src.ao3book.build import build_documents
from src.ao3book.config import Config, load_config
from src.ao3book.model import Chapter, Work
from src.ao3book.parser import parse_work
from src.ao3book.split import (
    SplitValidationError,
    group_chapters,
    split_work,
    split_work_manual,
    to_roman,
    validate_split_config,
    validate_split_coverage,
)

MULTI_FIXTURE = Path(__file__).parent / "fixtures" / "multi_chapter_sample.html"


def _fake_render(pages: int = 8):
    def render(html, out_path, base_url=None):
        render.calls.append((html, Path(out_path)))
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(width=419.5, height=595.3)
        with Path(out_path).open("wb") as f:
            writer.write(f)
    render.calls = []
    return render


# ---------- División automática existente ----------


def test_roman():
    assert [to_roman(n) for n in (1, 4, 9, 14, 40)] == ["I", "IV", "IX", "XIV", "XL"]


def test_group_respects_limit():
    assert group_chapters(front=5, pages=[40, 40, 40, 40], limit=100) == [[0, 1], [2, 3]]


def test_oversized_chapter_stays_alone():
    assert group_chapters(front=5, pages=[10, 500, 10], limit=100) == [[0], [1], [2]]


def test_balanced_parts():
    # el reparto goloso daría 90, 90, 90, 30; el balanceado, partes parecidas
    groups = group_chapters(front=0, pages=[30] * 10, limit=100)
    sizes = [sum(30 for _ in g) for g in groups]
    assert len(groups) == 4
    assert max(sizes) - min(sizes) <= 30
    assert min(sizes) > 30  # ya no queda una última parte diminuta


def test_balanced_keeps_all_chapters_in_order():
    groups = group_chapters(front=5, pages=[20, 35, 10, 50, 40, 15, 30], limit=100)
    assert [i for g in groups for i in g] == list(range(7))


def test_split_work_passes_toc_on_recto_to_measurement():
    work = Work(
        "Larga",
        "Autor",
        "<p>Resumen</p>",
        [Chapter(1, "Chapter 1", "<p>A</p>"), Chapter(2, "Chapter 2", "<p>B</p>")],
    )
    captured: list[str] = []

    def fake_render(html, out_path, base_url=None):
        captured.append(html)
        writer = PdfWriter()
        writer.add_blank_page(width=419.5, height=595.3)
        with open(out_path, "wb") as f:
            writer.write(f)

    split_work(work, Config(toc_on_recto=True), "/* css */", render=fake_render)
    assert '<nav class="toc recto">' in captured[0]

    split_work(work, Config(toc_on_recto=False), "/* css */", render=fake_render)
    assert '<nav class="toc">' in captured[1]


def test_split_work_auto_renumber_does_not_break_measurement(monkeypatch):
    work = Work(
        "Larga",
        "Autor",
        "<p>Resumen</p>",
        [
            Chapter(1, "Chapter 1: Uno", "<p>A</p>"),
            Chapter(2, "Chapter 2: Dos", "<p>B</p>"),
            Chapter(3, "Chapter 3: Tres", "<p>C</p>"),
            Chapter(4, "Chapter 4: Cuatro", "<p>D</p>"),
        ],
    )
    monkeypatch.setattr(
        "src.ao3book.split.measure_chapters",
        lambda w, css, render, toc_on_recto=False: (2, [40, 40, 40, 40]),
    )
    parts = split_work(
        work,
        Config(max_pages_per_part=100, renumber_chapters=True),
        "/* css */",
    )
    assert [p.title for p in parts] == ["Larga Part I", "Larga Part II"]
    assert [c.title for c in parts[0].chapters] == ["Chapter 1: Uno", "Chapter 2: Dos"]
    assert [c.title for c in parts[1].chapters] == ["Chapter 1: Tres", "Chapter 2: Cuatro"]
    # los números internos (usados en id="w1-c{n}") no mutan el Work original
    assert [c.title for c in work.chapters] == [
        "Chapter 1: Uno",
        "Chapter 2: Dos",
        "Chapter 3: Tres",
        "Chapter 4: Cuatro",
    ]
    assert [c.number for c in parts[1].chapters] == [3, 4]


# ---------- Momento A: validación de configuración (sin fixtures) ----------


def test_moment_a_valid_range_and_single_chapter():
    ranges = validate_split_config(
        [" 1-3 ", " 4 ", "5-8"],
        names=["Año 1", "Intermedio", "Final"],
        html_files=[Path("obra.html")],
    )
    assert ranges == [(1, 3), (4, 4), (5, 8)]


def test_moment_a_no_html_files():
    with pytest.raises(SplitValidationError) as exc:
        validate_split_config(["1-3", "4-6"], html_files=[])
    msg = str(exc.value)
    assert "input.dir" in msg and "ningún archivo .html" in msg


def test_moment_a_multiple_html_files():
    with pytest.raises(SplitValidationError) as exc:
        validate_split_config(["1-3", "4-6"], html_files=[Path("a.html"), Path("b.html")])
    msg = str(exc.value)
    assert "input.dir" in msg and "2 archivos .html" in msg


def test_moment_a_volumes_as_single_string_gives_list_error():
    with pytest.raises(SplitValidationError) as exc:
        validate_split_config("1-3, 4-5", html_files=[Path("a.html")])
    msg = str(exc.value)
    assert "lista" in msg and '["1-3", "4-5", "6-8"]' in msg


def test_moment_a_volumes_empty_or_missing():
    with pytest.raises(SplitValidationError):
        validate_split_config([], html_files=[Path("a.html")])
    with pytest.raises(SplitValidationError):
        validate_split_config(None, html_files=[Path("a.html")])


@pytest.mark.parametrize("bad", ["1-a", "1-3-5", "1-", "-3", "", "uno"])
def test_moment_a_invalid_format(bad):
    with pytest.raises(SplitValidationError) as exc:
        validate_split_config(["1-2", bad], html_files=[Path("a.html")])
    msg = str(exc.value)
    assert "split.volumes[2]" in msg and "formato inválido" in msg


@pytest.mark.parametrize("bad_list", [["0", "1-3"], ["0-3", "4-5"], ["1-0"]])
def test_moment_a_zero_chapter(bad_list):
    with pytest.raises(SplitValidationError) as exc:
        validate_split_config(bad_list, html_files=[Path("a.html")])
    msg = str(exc.value)
    assert "no puede ser 0" in msg and "split.volumes[1]" in msg


def test_moment_a_inverted_range():
    with pytest.raises(SplitValidationError) as exc:
        validate_split_config(["1-2", "5-3"], html_files=[Path("a.html")])
    msg = str(exc.value)
    assert "split.volumes[2]" in msg and "invertido" in msg and "3-5" in msg


def test_moment_a_overlap():
    with pytest.raises(SplitValidationError) as exc:
        validate_split_config(["1-3", "3-5"], html_files=[Path("a.html")])
    msg = str(exc.value)
    assert "split.volumes[2]" in msg and "solapamiento" in msg and "capítulo 3" in msg


def test_moment_a_gap():
    with pytest.raises(SplitValidationError) as exc:
        validate_split_config(["1-3", "6-7"], html_files=[Path("a.html")])
    msg = str(exc.value)
    assert "split.volumes[2]" in msg and "salto" in msg and "4 y 5" in msg


def test_moment_a_does_not_start_at_one():
    with pytest.raises(SplitValidationError) as exc:
        validate_split_config(["2-4", "5-6"], html_files=[Path("a.html")])
    msg = str(exc.value)
    assert "split.volumes[1]" in msg and "empezar en el capítulo 1" in msg


def test_moment_a_out_of_order():
    with pytest.raises(SplitValidationError) as exc:
        validate_split_config(["1-3", "6-7", "4-5"], html_files=[Path("a.html")])
    msg = str(exc.value)
    assert "split.volumes[3]" in msg and "orden ascendente" in msg


def test_moment_a_names_length_mismatch_and_empty():
    with pytest.raises(SplitValidationError) as exc:
        validate_split_config(["1-3", "4-6"], names=["Año 1"], html_files=[Path("a.html")])
    msg = str(exc.value)
    assert "split.names" in msg and "1 elemento(s)" in msg and "2" in msg

    with pytest.raises(SplitValidationError) as exc_empty:
        validate_split_config(["1-3", "4-6"], names=["Año 1", "   "], html_files=[Path("a.html")])
    assert "split.names[2]" in str(exc_empty.value) and "vacío" in str(exc_empty.value)


# ---------- Momento B: validación contra capítulos reales ----------


def _make_work(n_chapters: int) -> Work:
    return Work(
        title="Obra de prueba",
        author="Autor",
        summary_html="<p>Resumen</p>",
        chapters=[Chapter(i, f"Chapter {i}", f"<p>Cap {i}</p>") for i in range(1, n_chapters + 1)],
    )


def test_moment_b_range_exceeds_chapters():
    work = _make_work(6)
    with pytest.raises(SplitValidationError) as exc:
        validate_split_coverage([(1, 3), (4, 8)], work, raw_volumes=["1-3", "4-8"])
    msg = str(exc.value)
    assert "split.volumes[2]" in msg and "6 capítulos" in msg and "7 y 8" in msg


def test_moment_b_incomplete_coverage():
    work = _make_work(8)
    with pytest.raises(SplitValidationError) as exc:
        validate_split_coverage([(1, 3), (4, 5)], work, raw_volumes=["1-3", "4-5"])
    msg = str(exc.value)
    assert "split.volumes[2]" in msg and "8 capítulos" in msg and "6, 7 y 8" in msg


def test_moment_b_single_chapter_work():
    work = _make_work(1)
    with pytest.raises(SplitValidationError) as exc:
        validate_split_coverage([(1, 1)], work, raw_volumes=["1"])
    msg = str(exc.value)
    assert "un solo capítulo" in msg and "enabled = false" in msg


# ---------- División manual completa sobre fixture de ≥6 capítulos ----------


def test_manual_split_full_flow_with_and_without_renumber():
    work = parse_work(MULTI_FIXTURE)
    assert len(work.chapters) == 7

    ranges = validate_split_config(["1-3", "4", "5-7"], names=["Año 1", "Tormenta", "Final"])

    # renumber_chapters = False
    parts_orig = split_work_manual(
        work,
        ranges,
        names=["Año 1", "Tormenta", "Final"],
        renumber=False,
    )
    assert [p.title for p in parts_orig] == [
        "Crónicas del Norte Part I",
        "Crónicas del Norte Part II",
        "Crónicas del Norte Part III",
    ]
    assert [p.subtitle for p in parts_orig] == ["Año 1", "Tormenta", "Final"]
    assert [len(p.chapters) for p in parts_orig] == [3, 1, 3]
    assert all(p.summary_html == work.summary_html for p in parts_orig)
    assert all(p.author == "Autora Ejemplo" for p in parts_orig)
    assert [c.title for c in parts_orig[0].chapters] == ["Chapter 1", "Chapter 2: El viaje", "Chapter 3"]
    assert [c.title for c in parts_orig[1].chapters] == ["Chapter 4: La tormenta"]
    assert [c.title for c in parts_orig[2].chapters] == [
        "Chapter 5: El regreso",
        "Interlude",
        "Chapter 7: Epílogo",
    ]

    # El tomo de un solo capítulo conserva índice y encabezado
    single_vol = parts_orig[1]
    assert single_vol.is_part is True
    assert single_vol.show_toc is True
    assert single_vol.is_single_chapter is False

    docs = build_documents(parts_orig, Config(combine=False))
    assert [d.name for d in docs] == [
        "cronicas-del-norte-part-i-ano-1",
        "cronicas-del-norte-part-ii-tormenta",
        "cronicas-del-norte-part-iii-final",
    ]

    soup_single = BeautifulSoup(docs[1].html, "lxml")
    assert soup_single.find("h1", class_="work-title").get_text() == "Crónicas del Norte Part II"
    assert soup_single.find("p", class_="work-subtitle").get_text() == "Tormenta"
    assert soup_single.find("nav", class_="toc") is not None
    assert soup_single.find("h2", class_="chapter-title").get_text() == "Chapter 4: La tormenta"

    # renumber_chapters = True
    parts_renum = split_work_manual(
        work,
        ranges,
        names=["Año 1", "Tormenta", "Final"],
        renumber=True,
    )
    assert [c.title for c in parts_renum[0].chapters] == ["Chapter 1", "Chapter 2: El viaje", "Chapter 3"]
    assert [c.title for c in parts_renum[1].chapters] == ["Chapter 1: La tormenta"]
    assert [c.title for c in parts_renum[2].chapters] == [
        "Chapter 1: El regreso",
        "Interlude",
        "Chapter 2: Epílogo",
    ]

    # Verificar que los anclas del índice coinciden con los ids de artículo tras renumerar
    docs_renum = build_documents(parts_renum, Config(combine=False))
    soup_part3 = BeautifulSoup(docs_renum[2].html, "lxml")
    hrefs = [a["href"].lstrip("#") for a in soup_part3.select("nav.toc a")]
    article_ids = [art["id"] for art in soup_part3.select("article.chapter")]
    assert hrefs == article_ids and len(hrefs) == 3


# ---------- Interacciones en CLI (run) ----------


def test_run_manual_split_ignores_combine_and_auto_split_with_warnings(tmp_path, capsys):
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    shutil.copy(MULTI_FIXTURE, inp / "obra.html")

    render = _fake_render(pages=6)
    cfg = Config(
        input_dir=inp,
        output_dir=out,
        combine=True,
        split_enabled=True,
        split_long_works=True,
        split_volumes=("1-3", "4", "5-7"),
        split_names=("Año 1", "Tormenta", "Final"),
        format="booklet",
    )
    assert run(cfg, render) == 0
    err = capsys.readouterr().err
    assert "combine" in err and "no es un error" in err
    assert "split_long_works" in err and "división manual" in err

    pdfs = sorted(p.name for p in out.iterdir())
    assert pdfs == [
        "cronicas-del-norte-part-i-ano-1.pdf",
        "cronicas-del-norte-part-ii-tormenta.pdf",
        "cronicas-del-norte-part-iii-final.pdf",
    ]
    # Cada tomo impuesto como folleto aparte (6 páginas -> 8 -> 2 hojas -> 4 caras)
    for pdf_name in pdfs:
        reader = PdfReader(str(out / pdf_name))
        assert len(reader.pages) == 4
        assert float(reader.pages[0].mediabox.width) > float(reader.pages[0].mediabox.height)


def test_run_manual_split_validation_failure_aborts_before_generating_pdfs(tmp_path, capsys):
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    shutil.copy(MULTI_FIXTURE, inp / "obra.html")

    render = _fake_render()
    # Error de momento B (obra tiene 7 capítulos, rangos cubren solo hasta 5)
    cfg = Config(
        input_dir=inp,
        output_dir=out,
        split_enabled=True,
        split_volumes=("1-3", "4-5"),
    )
    assert run(cfg, render) == 1
    assert render.calls == []
    assert not out.exists() or list(out.iterdir()) == []
    assert "[error]" in capsys.readouterr().err


def test_run_moment_a_aborts_before_parsing_html(tmp_path, capsys):
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    # Archivo roto: si el parser llegara a leerlo imprimiría [aviso] roto.html
    (inp / "roto.html").write_text("<html><body>no es AO3</body></html>", encoding="utf-8")

    render = _fake_render()
    cfg = Config(
        input_dir=inp,
        output_dir=out,
        split_enabled=True,
        split_volumes="1-3, 4-5",
    )
    assert run(cfg, render) == 1
    err = capsys.readouterr().err
    assert "lista de textos" in err
    assert "roto.html" not in err
    assert render.calls == []


def test_run_split_disabled_ignores_volumes(tmp_path):
    inp = tmp_path / "input"
    out = tmp_path / "output"
    inp.mkdir()
    shutil.copy(MULTI_FIXTURE, inp / "obra.html")

    render = _fake_render()
    cfg = Config(
        input_dir=inp,
        output_dir=out,
        combine=False,
        split_enabled=False,
        split_volumes="esto no se valida si enabled=false",
    )
    assert run(cfg, render) == 0
    assert [p.name for p in out.iterdir()] == ["cronicas-del-norte.pdf"]


# ---------- Migración de configuración [book] -> [split] ----------


def test_config_migration_from_book_to_split(tmp_path, capsys):
    legacy = tmp_path / "legacy.toml"
    legacy.write_text(
        "[book]\nsplit_long_works = true\nmax_pages_per_part = 350\n",
        encoding="utf-8",
    )
    cfg = load_config(legacy)
    assert cfg.split_long_works is True
    assert cfg.max_pages_per_part == 350
    err = capsys.readouterr().err
    assert "book.split_long_works" in err and "[split]" in err
    assert "book.max_pages_per_part" in err and "[split]" in err

    both = tmp_path / "both.toml"
    both.write_text(
        "[book]\nsplit_long_works = false\nmax_pages_per_part = 200\n"
        "[split]\nsplit_long_works = true\nmax_pages_per_part = 550\n"
        'enabled = true\nvolumes = ["1-3", "4-6"]\nrenumber_chapters = true\n',
        encoding="utf-8",
    )
    cfg_both = load_config(both)
    assert cfg_both.split_long_works is True
    assert cfg_both.max_pages_per_part == 550
    assert cfg_both.split_enabled is True
    assert cfg_both.split_volumes == ("1-3", "4-6")
    assert cfg_both.renumber_chapters is True
    err_both = capsys.readouterr().err
    assert "se usa el valor de [split]" in err_both
