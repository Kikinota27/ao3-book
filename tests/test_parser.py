from pathlib import Path

import pytest

from src.ao3book.parser import normalize_chapter_title, parse_dir, parse_work

FIXTURE = Path(__file__).parent / "fixtures" / "the_first_hello.html"


@pytest.fixture(scope="module")
def work():
    return parse_work(FIXTURE)


def test_metadata(work):
    assert work.title == "The First Hello and Every Last Goodbye"
    assert work.author == "Seito"


def test_summary(work):
    assert "Sawada Tsunayoshi was a strange child" in work.summary_html
    assert "<blockquote" not in work.summary_html


def test_chapters(work):
    assert len(work.chapters) == 10
    assert [c.title for c in work.chapters] == [f"Chapter {i}" for i in range(1, 11)]
    assert [c.number for c in work.chapters] == list(range(1, 11))
    assert work.show_toc and not work.is_single_chapter


def test_notes_and_afterword_are_discarded(work):
    everything = " ".join(c.html for c in work.chapters) + work.summary_html
    assert "I love red herrings" not in everything
    assert "Chapter Notes" not in everything
    assert "drop by the Archive" not in everything


def test_html_is_clean(work):
    for chapter in work.chapters:
        assert "href" not in chapter.html
        assert "<a " not in chapter.html
        assert "<div" not in chapter.html
        assert chapter.html.startswith("<p>")


@pytest.mark.parametrize("raw, number, expected", [
    ("Chapter 1: Chapter 1", 1, "Chapter 1"),
    ("  Chapter 12:   Chapter 12 \n", 12, "Chapter 12"),
    ("chapter 3: chapter 3", 3, "Chapter 3"),
    ("Chapter 3: El comienzo", 3, "Chapter 3: El comienzo"),
    ("Chapter 3: Chapter 4", 3, "Chapter 3: Chapter 4"),
    ("Chapter 5", 5, "Chapter 5"),
    ("", 7, "Chapter 7"),
])
def test_normalize_chapter_title(raw, number, expected):
    assert normalize_chapter_title(raw, number) == expected


def _write(tmp_path, name, body, title="Una obra", author="Alguien"):
    html = f"""<html><head><title>{title} - {author} - Fandom</title></head><body>
    <div id="preface"><div class="meta"><h1>{title}</h1>
    <div class="byline">by <a rel="author" href="x">{author}</a></div>
    <p>Summary</p><blockquote class="userstuff"><p>Un resumen.</p></blockquote></div></div>
    {body}</body></html>"""
    path = tmp_path / name
    path.write_text(html, encoding="utf-8")
    return path


def test_single_chapter_direct_text(tmp_path):
    path = _write(tmp_path, "uno.html",
                  '<div id="chapters" class="userstuff"><p>Hola <a href="x">mundo</a>.</p></div>')
    w = parse_work(path)
    assert w.is_single_chapter and not w.show_toc
    assert w.chapters[0].html == "<p>Hola mundo.</p>"


def test_single_chapter_with_userstuff_div(tmp_path):
    body = ('<div id="chapters"><div class="meta group"><h2 class="heading"> Chapter 1: Chapter 1 </h2></div>'
            '<div class="userstuff"><p>Texto.</p></div></div>')
    w = parse_work(_write(tmp_path, "dos.html", body))
    assert w.is_single_chapter
    assert w.chapters[0].title == "Chapter 1"


def test_chapter_with_real_title(tmp_path):
    body = ('<div id="chapters">'
            '<div class="meta group"><h2 class="heading">Chapter 1: Inicio</h2></div><div class="userstuff"><p>A</p></div>'
            '<div class="meta group"><h2 class="heading">Chapter 2: Chapter 2</h2></div><div class="userstuff"><p>B</p></div>'
            '</div>')
    w = parse_work(_write(tmp_path, "tres.html", body))
    assert [c.title for c in w.chapters] == ["Chapter 1: Inicio", "Chapter 2"]


def test_centered_paragraph_and_empty_paragraphs(tmp_path):
    body = ('<div id="chapters" class="userstuff"><p align="center">Centro</p><p>&nbsp;</p>'
            '<p style="text-align: center">Otro</p><p>Normal</p></div>')
    html = parse_work(_write(tmp_path, "cuatro.html", body)).chapters[0].html
    assert html == '<p class="center">Centro</p><p class="center">Otro</p><p>Normal</p>'


def test_parse_dir_skips_broken_files(tmp_path, capsys):
    _write(tmp_path, "bien.html", '<div id="chapters"><p>Texto</p></div>')
    (tmp_path / "roto.html").write_text("<html><body>nada</body></html>", encoding="utf-8")
    works = parse_dir(tmp_path)
    assert len(works) == 1
    assert "roto.html" in capsys.readouterr().err
