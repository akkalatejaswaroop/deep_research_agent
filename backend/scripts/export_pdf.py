"""PDF Export Generator for REX — Recursive Exploration eXplorer.

Converts markdown reports to professionally styled PDF documents.
Can be called standalone or integrated as an API endpoint.
"""

import os
import re
from datetime import datetime
from fpdf import FPDF


def markdown_to_pdf(report_md: str, query: str = "", output_path: str = "",
                    session_id: str = "") -> str:
    if not output_path:
        safe_name = re.sub(r'[^a-z0-9]', '_', query.lower())[:50] if query else "research_report"
        output_path = f"{safe_name}_report.pdf"

    pdf = PDFReport(query=query or "REX Research Report")
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()

    lines = report_md.split("\n")
    in_code_block = False
    code_lines = []
    in_table = False

    for line in lines:
        if line.startswith("```"):
            if in_code_block:
                pdf.render_code_block("\n".join(code_lines))
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if not line.strip():
            pdf.ln(2)
            continue

        if line.startswith("# "):
            pdf.render_heading(line[2:].strip(), 1)
        elif line.startswith("## "):
            pdf.render_heading(line[3:].strip(), 2)
        elif line.startswith("### "):
            pdf.render_heading(line[4:].strip(), 3)
        elif line.startswith("#### "):
            pdf.render_heading(line[5:].strip(), 4)
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            pdf.render_list_item(line.strip()[2:])
        elif re.match(r"^\s*\d+\.\s", line.strip()):
            text = re.sub(r"^\s*\d+\.\s", "", line.strip())
            pdf.render_list_item(text)
        elif line.strip().startswith(">"):
            pdf.render_blockquote(line.strip()[1:].strip())
        elif re.match(r"^[-=]{3,}$", line.strip()):
            pdf.render_hr()
        else:
            pdf.render_paragraph(line.strip())

    pdf.output(output_path)
    return output_path


class PDFReport(FPDF):
    def __init__(self, query: str):
        super().__init__("P", "mm", "A4")
        self.query = query

        fonts_dir = os.environ.get("WINDIR", "C:\\Windows") + "\\Fonts"
        self.add_font("ArialUni", "", os.path.join(fonts_dir, "arial.ttf"), uni=True)
        self.add_font("ArialUni", "B", os.path.join(fonts_dir, "arialbd.ttf"), uni=True)
        self.add_font("ArialUni", "I", os.path.join(fonts_dir, "ariali.ttf"), uni=True)
        self.add_font("ArialUni", "BI", os.path.join(fonts_dir, "arialbi.ttf"), uni=True)
        self.add_font("CourierNew", "", os.path.join(fonts_dir, "cour.ttf"), uni=True)
        self.add_font("CourierNew", "B", os.path.join(fonts_dir, "courbd.ttf"), uni=True)

        self.FONT = "ArialUni"
        self.FONT_MONO = "CourierNew"
        self.C_PRIMARY = (212, 168, 83)
        self.C_TEXT = (40, 40, 40)
        self.C_MUTED = (120, 120, 120)
        self.C_SECONDARY = (90, 90, 90)
        self.C_BORDER = (210, 208, 204)
        self.C_CODE_BG = (242, 240, 236)

    def header(self):
        if self.page_no() == 1:
            self.set_fill_color(*self.C_PRIMARY)
            self.rect(0, 0, 210, 3, "F")
            self.set_y(22)
            self.set_font(self.FONT, "B", 22)
            self.set_text_color(*self.C_TEXT)
            self.cell(0, 9, "REX Research Report", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font(self.FONT, "I", 10)
            self.set_text_color(*self.C_MUTED)
            q = (self.query[:80] + "...") if len(self.query) > 80 else self.query
            self.cell(0, 5, "Query: " + q, align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font(self.FONT, "", 8)
            self.set_text_color(*self.C_MUTED)
            self.cell(0, 4, "Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M"), align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(*self.C_BORDER)
            self.set_y(50)
            self.line(20, self.get_y(), 190, self.get_y())
            self.ln(6)
        else:
            self.set_fill_color(*self.C_PRIMARY)
            self.rect(0, 0, 210, 1.5, "F")
            self.set_y(5)
            self.set_font(self.FONT, "I", 7)
            self.set_text_color(*self.C_MUTED)
            q = self.query[:60]
            self.cell(90, 5, q, align="L")
            self.cell(90, 5, "Page " + str(self.page_no()), align="R", new_x="LMARGIN", new_y="NEXT")

    def footer(self):
        self.set_y(-15)
        self.set_font(self.FONT, "", 7)
        self.set_text_color(*self.C_MUTED)
        self.cell(0, 10, "REX — Recursive Exploration eXplorer", align="C")

    def render_heading(self, text, level):
        sizes = {1: 16, 2: 13, 3: 11, 4: 10}
        colors = {1: self.C_TEXT, 2: self.C_PRIMARY, 3: self.C_TEXT, 4: self.C_MUTED}
        self.set_font(self.FONT, "B", sizes.get(level, 11))
        self.set_text_color(*colors.get(level, self.C_TEXT))
        if level == 1:
            self.ln(3)
        self.multi_cell(0, 6 + (3 - level), text)
        if level <= 2:
            self.set_draw_color(*self.C_BORDER)
            self.line(self.l_margin, self.get_y(), self.l_margin + 35, self.get_y())
        self.ln(2)

    def render_paragraph(self, text):
        self.set_font(self.FONT, "", 9)
        self.set_text_color(*self.C_TEXT)
        self.multi_cell(0, 4.5, text)
        self.ln(0.5)

    def render_list_item(self, text):
        self.set_x(self.l_margin + 5)
        self.set_font(self.FONT, "", 9)
        self.set_text_color(*self.C_TEXT)
        self.multi_cell(0, 4.5, "-  " + text)
        self.ln(0.3)

    def render_blockquote(self, text):
        self.set_x(self.l_margin + 5)
        y_start = self.get_y()
        self.set_font(self.FONT, "I", 9)
        self.set_text_color(*self.C_MUTED)
        self.multi_cell(160, 4.5, text)
        y_end = self.get_y()
        self.set_draw_color(*self.C_PRIMARY)
        self.set_line_width(0.4)
        self.line(self.l_margin + 2, y_start, self.l_margin + 2, y_end + 1)
        self.set_line_width(0.2)
        self.ln(2)

    def render_code_block(self, code):
        self.set_fill_color(*self.C_CODE_BG)
        self.set_draw_color(*self.C_BORDER)
        y_start = self.get_y()
        self.set_font(self.FONT_MONO, "", 7)
        self.set_text_color(*self.C_SECONDARY)
        self.set_x(self.l_margin + 4)
        self.multi_cell(172, 4, code)
        y_end = self.get_y()
        self.rect(self.l_margin + 2, y_start, 176, y_end - y_start + 2, "F")
        self.set_xy(self.l_margin + 4, y_start + 1)
        self.set_font(self.FONT_MONO, "", 7)
        self.set_text_color(*self.C_SECONDARY)
        self.multi_cell(172, 4, code)
        self.ln(3)

    def render_hr(self):
        self.set_draw_color(*self.C_BORDER)
        y = self.get_y() + 2
        self.line(self.l_margin, y, 210 - self.l_margin, y)
        self.ln(4)


if __name__ == "__main__":
    sample = """# Test Report

## Section 1
Some paragraph text here.

- List item one
- List item two

> A blockquote example

### Code
```
print("hello")
```
"""
    out = markdown_to_pdf(sample, "Test", "test_report.pdf")
    print(f"PDF: {out} ({os.path.getsize(out)} bytes)")
