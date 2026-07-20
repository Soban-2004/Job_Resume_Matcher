from fpdf import FPDF, XPos, YPos

from app.models.schemas import OptimizedResume

# fpdf2's core fonts (Helvetica/Times/Courier) only support Latin-1 -- resumes
# routinely carry Unicode punctuation (en/em dashes, curly quotes, bullets)
# that would otherwise raise an encoding error mid-render. Swapping to the
# closest ASCII equivalent is simpler and more portable than bundling a
# Unicode TTF font just for this.
_UNICODE_REPLACEMENTS = {
    "–": "-", "—": "-",  # en dash, em dash
    "‘": "'", "’": "'",  # curly single quotes
    "“": '"', "”": '"',  # curly double quotes
    "•": "-", "‣": "-", "◦": "-",  # bullet variants
    "…": "...",  # ellipsis
}


def _sanitize(text: str) -> str:
    for src, dest in _UNICODE_REPLACEMENTS.items():
        text = text.replace(src, dest)
    return text.encode("latin-1", "replace").decode("latin-1")


def render_resume_pdf(resume: OptimizedResume) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(18, 16, 18)
    pdf.add_page()

    if resume.full_name:
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 9, _sanitize(resume.full_name), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if resume.contact_line:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(90, 90, 90)
        pdf.cell(0, 6, _sanitize(resume.contact_line), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)

    pdf.ln(2)

    for section in resume.sections:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, _sanitize(section.heading.upper()), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(60, 60, 60)
        pdf.set_line_width(0.4)
        y = pdf.get_y()
        pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
        pdf.ln(3)

        pdf.set_font("Helvetica", "", 10.5)
        for line in section.lines:
            pdf.multi_cell(0, 5.5, _sanitize(f"- {line}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    return bytes(pdf.output())
