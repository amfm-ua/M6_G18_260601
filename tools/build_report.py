#!/usr/bin/env python3
"""Gera o relatório consolidado M6 a partir dos capítulos.

Fonte única de verdade: os ficheiros de capítulo `NN_*.md` em `m6_markdowns/`.
Este script concatena, por ordem numérica:

    _capa.md  +  (Índice gerado)  +  00_*.md … 15_*.md

e reescreve `M6_G18_260601_LIVE.md`. Editam-se SÓ os capítulos; o LIVE é um
artefacto regenerável — nunca se edita à mão.

O rodapé de trabalho de cada capítulo (`--- / *Ficheiro de trabalho…*`) é
removido na consolidação. O índice é gerado automaticamente a partir dos
títulos `#`/`##` (sem números de página — no Word, usar Referências → Índice).

Uso:
    python tools/build_report.py            # gera o LIVE.md
    python tools/build_report.py --docx     # gera também .docx (requer pandoc)
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "m6_markdowns"
CAPA = ROOT / "_capa.md"
OUT = ROOT / "M6_G18_260601_LIVE.md"
DOCX = ROOT / "M6_G18_260601_LIVE.docx"

# Rodapé de trabalho no fim de cada capítulo (removido na consolidação).
FOOTER_RE = re.compile(
    r"\n*-{3,}[ \t]*\n+\*Ficheiro de trabalho[^\n]*\*[ \t]*\n*\Z"
)


def load(path: Path) -> str:
    """Lê um markdown, remove o rodapé de trabalho e espaços nas pontas."""
    text = path.read_text(encoding="utf-8")
    text = FOOTER_RE.sub("", text)
    return text.strip()


def slug(title: str) -> str:
    """Âncora estilo GitHub: minúsculas, sem pontuação, espaços→hífen."""
    s = unicodedata.normalize("NFC", title).lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    return re.sub(r"\s+", "-", s.strip())


def build_toc(body: str) -> str:
    """Índice markdown a partir dos títulos H1/H2 (ignora blocos de código)."""
    lines, in_code = [], False
    for ln in body.splitlines():
        if ln.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^(#{1,2})\s+(.*)$", ln)
        if not m:
            continue
        level, title = len(m.group(1)), m.group(2).strip()
        indent = "  " * (level - 1)
        lines.append(f"{indent}- [{title}](#{slug(title)})")
    return "# Índice\n\n" + "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--docx", action="store_true", help="gerar .docx via pandoc")
    ap.add_argument(
        "--no-toc", action="store_true", help="não gerar índice (deixar ao Word)"
    )
    args = ap.parse_args()

    chapters = sorted(ROOT.glob("[0-9][0-9]_*.md"))
    if not chapters:
        print("ERRO: nenhum capítulo NN_*.md encontrado em", ROOT, file=sys.stderr)
        return 1

    body = "\n\n".join(load(c) for c in chapters)

    parts = []
    if CAPA.exists():
        parts.append(load(CAPA))
    if not args.no_toc:
        parts.append(build_toc(body))
    parts.append(body)

    OUT.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(f"OK  {OUT.name}  ({len(chapters)} capítulos, {OUT.stat().st_size:,} bytes)")

    if args.docx:
        pandoc = shutil.which("pandoc")
        if pandoc:
            subprocess.run(
                [pandoc, str(OUT), "-o", str(DOCX), "--toc"], check=True
            )
            print(f"OK  {DOCX.name} gerado via pandoc")
        else:
            # Fallback: pandoc embutido no pypandoc (pip install pypandoc_binary).
            try:
                import pypandoc
            except ImportError:
                print(
                    "AVISO: pandoc não encontrado no PATH e pypandoc não instalado "
                    "— .docx não gerado.\n        Instale com: pip install pypandoc_binary"
                )
                return 0
            pypandoc.convert_file(
                str(OUT), "docx", outputfile=str(DOCX), extra_args=["--toc"]
            )
            print(f"OK  {DOCX.name} gerado via pypandoc (pandoc embutido)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
