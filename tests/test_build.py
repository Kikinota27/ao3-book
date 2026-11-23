from dataclasses import replace
from pathlib import Path

from bs4 import BeautifulSoup

from src.ao3book.build import build_css, build_documents, slugify
from src.ao3book.config import Config, load_config
from src.ao3book.model import Chapter, Work
from src.ao3book.parser import parse_work

FIXTURE = Path(__file__).parent / "fixtures" / "the_first_hello.html"


def make_work(title, source=None):
    return Work(title, "Autor", "<p>Resumen</p>", [Chapter(1, "Chapter 1", "<p>Texto</p>")], source)


def titles(doc):
    return [h.get_text() for h in BeautifulSoup(doc.html, "lxml").select("h1.work-title")]


def test_combine_true_gives_one_sorted_document():
    docs = build_documents([make_work("zeta"), make_work("Alpha"), make_work("mango")], Config(combine=True))
    assert len(docs) == 1 and docs[0].name == "libro"
    assert titles(docs[0]) == ["Alpha", "mango", "zeta"]  # orden alfabético sin distinguir mayúsculas
    soup = BeautifulSoup(docs[0].html, "lxml")
    assert soup.title.get_text() == "Libro"
    assert all("recto" in s["class"] for s in soup.select("section.work"))


def test_combine_false_gives_one_document_per_work():
    docs = build_documents([make_work("Zeta"), make_work("Alpha")], Config(combine=False))
    assert [d.name for d in docs] == ["alpha", "zeta"]
    assert [titles(d) for d in docs] == [["Alpha"], ["Zeta"]]
    for d in docs:
        soup = BeautifulSoup(d.html, "lxml")
        assert "recto" not in soup.find("section")["class"]
        assert soup.title.get_text() == titles(d)[0]


def test_combine_false_unique_and_safe_file_names():
    works = [make_work("Mi obra: ¿qué?"), make_work("Mi obra: ¿qué?"), make_work("日本語", Path("x/raw_file.html")),
             make_work("???")]
    names = [d.name for d in build_documents(works, Config(combine=False))]
    assert len(set(names)) == 4
    assert "mi-obra-que" in names and "mi-obra-que-2" in names
    assert "raw_file" not in names and "raw-file" in names     # título sin ascii -> usa el archivo
    assert "obra-4" in names or any(n.startswith("obra-") for n in names)


def test_single_work_combined_uses_its_title():
    doc = build_documents([make_work("Sola")], Config(combine=True))[0]
    assert BeautifulSoup(doc.html, "lxml").title.get_text() == "Sola"


def test_empty_list_gives_no_documents():
    assert build_documents([], Config()) == []


def test_css_has_variables_page_rules_and_base_styles():
    css = build_css(replace(Config(), format="a4"))
    assert "--font-size: 11pt;" in css
    assert "size: 210mm 297mm" in css
    assert ".chapter-title" in css
    assert css.index(":root") < css.index("@page {") < css.index(".chapter-title")


def test_format_changes_page_size_in_document():
    work = parse_work(FIXTURE)
    a5 = build_documents([work], Config(format="a5"))[0].html
    booklet = build_documents([work], Config(format="booklet", booklet_sheet="letter"))[0].html
    assert "size: 148mm 210mm" in a5
    assert "size: 139.7mm 215.9mm" in booklet


def test_slugify():
    assert slugify("The First Hello & Every Last Goodbye") == "the-first-hello-every-last-goodbye"
    assert slugify("  Ñandú — día  ") == "nandu-dia"
    assert slugify("日本語") == ""


def test_toc_page_break_css_and_config(tmp_path):
    css = build_css(Config())
    assert ".toc { break-before: page; }" in css
    assert ".toc.recto { break-before: right; }" in css

    work = Work(
        "Dos capítulos",
        "Autor",
        "<p>Resumen</p>",
        [Chapter(1, "Chapter 1", "<p>A</p>"), Chapter(2, "Chapter 2", "<p>B</p>")],
    )
    for combine in (True, False):
        doc_no_blank = build_documents([work], Config(combine=combine, toc_on_recto=False))[0]
        doc_blank = build_documents([work], Config(combine=combine, toc_on_recto=True))[0]
        assert "recto" not in BeautifulSoup(doc_no_blank.html, "lxml").find("nav", class_="toc")["class"]
        assert "recto" in BeautifulSoup(doc_blank.html, "lxml").find("nav", class_="toc")["class"]

    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text("[book]\ntoc_on_recto = true\n", encoding="utf-8")
    assert load_config(cfg_path).toc_on_recto is True

    cfg_default = tmp_path / "default.toml"
    cfg_default.write_text("[book]\n", encoding="utf-8")
    assert load_config(cfg_default).toc_on_recto is False
