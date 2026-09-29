"""Genera el PDF de un documento Markdown de docs/ (mismo nombre, extensión .pdf).

Uso:  python docs/generar_pdf.py docs/matriz-principios.md [otro.md ...]
Requiere: pip install markdown  y  Microsoft Edge o Google Chrome (se usa en modo headless).
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

NAVEGADORES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "msedge", "google-chrome", "chromium", "chrome",
]

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #1f2328; }
h1 { font-size: 20pt; color: #0b3d5c; border-bottom: 3px solid #0171ad; padding-bottom: 6px; }
h2 { font-size: 15pt; color: #0b3d5c; margin-top: 22px; border-bottom: 1px solid #d0d7de; padding-bottom: 3px; }
h3 { font-size: 12.5pt; color: #0171ad; margin-top: 16px; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th { background: #0b3d5c; color: white; text-align: left; }
th, td { border: 1px solid #d0d7de; padding: 5px 7px; vertical-align: top; }
tr:nth-child(even) td { background: #f6f8fa; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #eef2f6; padding: 1px 4px; border-radius: 3px; }
pre { background: #1f2430; color: #e6e6e6; padding: 10px 12px; border-radius: 6px; overflow: hidden;
      white-space: pre-wrap; page-break-inside: avoid; }
pre code { background: none; color: inherit; padding: 0; }
blockquote { margin: 8px 0; padding: 6px 12px; border-left: 4px solid #0171ad; background: #eef6fb; color: #33424f; }
a { color: #0171ad; text-decoration: none; }
hr { border: none; border-top: 1px solid #d0d7de; margin: 16px 0; }
img { max-width: 100%; }
"""


def navegador() -> str:
    for candidato in NAVEGADORES:
        if Path(candidato).exists() or shutil.which(candidato):
            return candidato
    sys.exit("No se encontró Edge ni Chrome para generar el PDF.")


def generar(md_path: Path) -> Path:
    html_cuerpo = markdown.markdown(md_path.read_text(encoding="utf-8"),
                                    extensions=["tables", "fenced_code", "sane_lists"])
    titulo = md_path.stem.replace("-", " ").capitalize()
    html = (f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{titulo}</title>'
            f"<style>{CSS}</style></head><body>{html_cuerpo}</body></html>")
    pdf_path = md_path.with_suffix(".pdf")
    # El HTML temporal va junto al .md para que las imágenes relativas se resuelvan.
    with tempfile.NamedTemporaryFile("w", suffix=".html", dir=md_path.parent, delete=False,
                                     encoding="utf-8") as tmp:
        tmp.write(html)
    try:
        subprocess.run([navegador(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf_path.resolve()}", Path(tmp.name).resolve().as_uri()],
                       check=True, capture_output=True, timeout=120)
    finally:
        Path(tmp.name).unlink(missing_ok=True)
    return pdf_path


if __name__ == "__main__":
    for arg in sys.argv[1:] or sys.exit(__doc__):
        print("PDF:", generar(Path(arg)))
