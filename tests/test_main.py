import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from src.ao3book.__main__ import main, parse_args, run
from src.ao3book.config import Config

FIXTURE = Path(__file__).parent / "fixtures" / "the_first_hello.html"


def fake_render(pages=10):
    """Reemplaza a WeasyPrint: escribe un PDF en blanco con `pages` páginas."""
    def render(html, out_path, base_url=None):
        render.calls.append(html)
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(width=419.5, height=595.3)
        with Path(out_path).open("wb") as f:
            writer.write(f)
    render.calls = []
    return render


def project(tmp_path, n_files=2, **config):
    inp = tmp_path / "input"
    inp.mkdir()
    for i in range(n_files):
        shutil.copy(FIXTURE, inp / f"obra{i}.html")
    return Config(input_dir=inp, output_dir=tmp_path / "output", **config)


def test_combine_true_makes_one_pdf(tmp_path):
    render = fake_render()
    assert run(project(tmp_path, combine=True), render) == 0
    assert [p.name for p in (tmp_path / "output").iterdir()] == ["libro.pdf"]
    assert len(render.calls) == 1
    assert render.calls[0].count('<section class="work') == 2   # las dos obras en el mismo documento


def test_combine_false_makes_one_pdf_per_work(tmp_path):
    render = fake_render()
    assert run(project(tmp_path, combine=False), render) == 0
    names = sorted(p.name for p in (tmp_path / "output").iterdir())
    assert names == ["the-first-hello-and-every-last-goodbye-2.pdf", "the-first-hello-and-every-last-goodbye.pdf"]
    assert len(render.calls) == 2


def test_booklet_imposes_pages(tmp_path):
    cfg = project(tmp_path, combine=True, format="booklet")
    assert run(cfg, fake_render(pages=10)) == 0
    out = PdfReader(str(tmp_path / "output" / "libro.pdf"))
    assert len(out.pages) == 6                                   # 10 -> 12 páginas -> 3 hojas -> 6 caras
    assert float(out.pages[0].mediabox.width) > float(out.pages[0].mediabox.height)  # hoja apaisada


def test_missing_input_dir_or_no_works_returns_error(tmp_path):
    assert run(Config(input_dir=tmp_path / "nope", output_dir=tmp_path / "out"), fake_render()) == 1
    (tmp_path / "vacia").mkdir()
    assert run(Config(input_dir=tmp_path / "vacia", output_dir=tmp_path / "out"), fake_render()) == 1


def test_broken_input_file_is_skipped(tmp_path):
    cfg = project(tmp_path, n_files=1)
    (cfg.input_dir / "roto.html").write_text("<html><body>nada</body></html>", encoding="utf-8")
    assert run(cfg, fake_render()) == 0
    assert (tmp_path / "output" / "libro.pdf").exists()


def test_render_failure_on_one_document_does_not_stop_the_rest(tmp_path):
    good = fake_render()
    def flaky(html, out_path, base_url=None):
        if "-2" in str(out_path):
            raise ValueError("boom")
        good(html, out_path)
    assert run(project(tmp_path, combine=False), flaky) == 1       # hubo un error...
    assert (tmp_path / "output" / "the-first-hello-and-every-last-goodbye.pdf").exists()  # ...pero salió el otro


def test_runtime_error_aborts_with_error_code(tmp_path):
    def no_weasyprint(html, out_path, base_url=None):
        raise RuntimeError("falta WeasyPrint")
    assert run(project(tmp_path), no_weasyprint) == 1


def test_args_and_config_errors(tmp_path):
    assert parse_args([]).config == "config.toml" and parse_args([]).format is None
    assert parse_args(["--format", "A5"]).format == "a5"
    with pytest.raises(SystemExit):
        parse_args(["--format", "a3"])
    assert main(["--config", str(tmp_path / "no_existe.toml")]) == 1
    bad = tmp_path / "bad.toml"
    bad.write_text('[book]\nformat = "a3"\n', encoding="utf-8")
    assert main(["--config", str(bad)]) == 1


def test_run_prints_input_file_count_at_start(tmp_path, capsys):
    inp = tmp_path / "input"
    inp.mkdir()
    html = (
        '<html><body><div id="preface"><div class="meta"><h1>Obra</h1></div></div>'
        '<div id="chapters"><div class="meta group"><h2>Chapter 1</h2></div>'
        '<div class="userstuff"><p>A</p></div>'
        '<div class="meta group"><h2>Chapter 2</h2></div>'
        '<div class="userstuff"><p>B</p></div></div></body></html>'
    )
    for i in range(3):
        (inp / f"obra{i}.html").write_text(html, encoding="utf-8")
    (inp / "notas.txt").write_text("ignorar", encoding="utf-8")

    base_render = fake_render()
    seen_before_first_render = []

    def tracking_render(doc_html, out_path, base_url=None):
        if not seen_before_first_render:
            seen_before_first_render.append(capsys.readouterr().out)
        base_render(doc_html, out_path, base_url)

    cfg = Config(input_dir=inp, output_dir=tmp_path / "output", combine=True, split_long_works=True)
    assert run(cfg, tracking_render) == 0
    assert seen_before_first_render == [f"Procesando 3 archivo(s) de entrada en {inp}...\n"]
    remaining = capsys.readouterr().out
    assert "3 obra(s)" in remaining
