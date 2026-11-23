"""HTML -> PDF con WeasyPrint."""
from __future__ import annotations

from pathlib import Path


def render_pdf(html: str, out_path: str | Path, base_url: str | Path | None = None) -> Path:
    """Convierte un string HTML en un PDF y devuelve la ruta de salida."""
    try:
        from weasyprint import HTML
    except ImportError as e:  # falta instalar o faltan librerías del sistema
        raise RuntimeError(
            "No se pudo importar WeasyPrint. Instalalo con 'pip install weasyprint' "
            "y revisá https://doc.courtbouillon.org/weasyprint/stable/first_steps.html "
            "para las dependencias del sistema (Pango)."
        ) from e

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html, base_url=str(base_url) if base_url else None).write_pdf(out_path)
    return out_path
