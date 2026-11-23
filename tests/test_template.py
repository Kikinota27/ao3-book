from pathlib import Path

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader

from src.ao3book.model import Chapter, Work
from src.ao3book.parser import parse_work

ROOT = Path(__file__).parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "the_first_hello.html"


def render(works, **extra):
    env = Environment(loader=FileSystemLoader(ROOT / "src" / "ao3book" / "templates"),
                      autoescape=True, trim_blocks=True, lstrip_blocks=True)
    ctx = dict(works=works, css="/* css */", doc_title="Libro", start_on_recto=True)
    ctx.update(extra)
    return BeautifulSoup(env.get_template("book.html.j2").render(**ctx), "lxml")


def test_multi_chapter_work_structure():
    soup = render([parse_work(FIXTURE)])
    assert soup.find("h1", class_="work-title").get_text() == "The First Hello and Every Last Goodbye"
    assert soup.find("p", class_="work-author").get_text() == "Seito"
    assert "strange child" in soup.find(class_="work-summary").get_text()
    assert len(soup.select("nav.toc li")) == 10
    assert len(soup.select("article.chapter")) == 10
    assert [h.get_text() for h in soup.select("h2.chapter-title")][:2] == ["Chapter 1", "Chapter 2"]


def test_order_front_toc_chapters():
    soup = render([parse_work(FIXTURE)])
    section = soup.find("section", class_="work")
    names = [el.name + "." + (el.get("class") or [""])[0] for el in section.find_all(["header", "article"], recursive=False)]
    assert names[0] == "header.work-front" and set(names[1:]) == {"article.chapter"}


def test_toc_links_point_to_existing_chapters():
    soup = render([parse_work(FIXTURE), parse_work(FIXTURE)])
    ids = {el["id"] for el in soup.find_all(id=True)}
    hrefs = [a["href"][1:] for a in soup.select("nav.toc a")]
    assert len(hrefs) == 20 and all(h in ids for h in hrefs)
    assert len(ids) == len(soup.find_all(id=True))  # ids únicos aunque se repita la obra


def test_single_chapter_has_no_toc_nor_chapter_heading():
    work = Work("Corta", "Yo", "<p>Resumen</p>", [Chapter(1, "Chapter 1", "<p>Texto</p>")])
    soup = render([work])
    assert soup.find("nav") is None
    assert soup.find("h2") is None
    assert soup.find("section", class_="single") is not None
    assert "Texto" in soup.find("article").get_text()


def test_optional_parts_and_escaping():
    work = Work("A & B <i>", "", "", [Chapter(1, "Chapter 1", "<p>x</p>")])
    soup = render([work], start_on_recto=False)
    assert soup.find("h1").get_text() == "A & B <i>"      # título escapado
    assert soup.find(class_="work-author") is None
    assert soup.find(class_="work-summary") is None
    assert "recto" not in soup.find("section")["class"]


def test_toc_on_recto_adds_recto_class_to_toc():
    work = Work(
        "Larga",
        "Yo",
        "<p>Resumen</p>",
        [Chapter(1, "Chapter 1", "<p>A</p>"), Chapter(2, "Chapter 2", "<p>B</p>")],
    )
    default_soup = render([work])
    assert "recto" not in default_soup.find("nav", class_="toc")["class"]

    recto_soup = render([work], toc_on_recto=True)
    assert "recto" in recto_soup.find("nav", class_="toc")["class"]
