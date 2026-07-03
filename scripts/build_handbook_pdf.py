"""Build HANDBOOK.pdf from HANDBOOK.md with deterministic local formatting."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos


class HandbookPDF(FPDF):
    def header(self) -> None:  # noqa: D401
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            8,
            "enterprise-okf-ai handbook",
            border=0,
            align="R",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.ln(1)

    def footer(self) -> None:  # noqa: D401
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", border=0, align="C")


def _clean_text(value: str) -> str:
    return value.encode("latin-1", "replace").decode("latin-1")


def _write_wrapped(pdf: FPDF, text: str, line_height: float) -> None:
    usable_width = max(20.0, pdf.w - pdf.l_margin - pdf.r_margin)
    pdf.multi_cell(usable_width, line_height, _clean_text(text), wrapmode="CHAR")


def build_pdf(source_md: Path, output_pdf: Path) -> None:
    if not source_md.exists():
        raise FileNotFoundError(f"Handbook markdown not found: {source_md}")

    lines = source_md.read_text(encoding="utf-8").splitlines()

    pdf = HandbookPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    in_code_block = False
    for raw_line in lines:
        line = raw_line.rstrip("\n")

        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            pdf.ln(1)
            continue

        if in_code_block:
            pdf.set_font("Courier", "", 9)
            pdf.set_text_color(35, 35, 35)
            _write_wrapped(pdf, line if line else " ", 4.5)
            continue

        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(20, 20, 20)
            _write_wrapped(pdf, line[2:].strip(), 9)
            pdf.ln(1)
            continue

        if line.startswith("## "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(30, 30, 30)
            _write_wrapped(pdf, line[3:].strip(), 7)
            pdf.ln(0.5)
            continue

        if line.startswith("### "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(40, 40, 40)
            _write_wrapped(pdf, line[4:].strip(), 6)
            continue

        if line.startswith("- "):
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(20, 20, 20)
            _write_wrapped(pdf, f"- {line[2:].strip()}", 5.8)
            continue

        if line.strip() == "":
            pdf.ln(2)
            continue

        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(20, 20, 20)
        _write_wrapped(pdf, line, 5.8)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_pdf))


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source_md = root / "HANDBOOK.md"
    output_pdf = root / "HANDBOOK.pdf"
    build_pdf(source_md, output_pdf)
    print(output_pdf.as_posix())


if __name__ == "__main__":
    main()
