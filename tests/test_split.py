from ao3book.config import Config
from ao3book.model import Chapter, Work
from ao3book.split import group_chapters, split_work, to_roman

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
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=419.5, height=595.3)
        with open(out_path, "wb") as f:
            writer.write(f)

    split_work(work, Config(toc_on_recto=True), "/* css */", render=fake_render)
    assert '<nav class="toc recto">' in captured[0]

    split_work(work, Config(toc_on_recto=False), "/* css */", render=fake_render)
    assert '<nav class="toc">' in captured[1]