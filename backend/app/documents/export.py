from io import BytesIO
from pathlib import Path
from threading import Lock
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

MIME_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}
FONT_PATHS = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("C:/Windows/Fonts/arial.ttf"),
)
FONT_NAME = "ThemisDocument"
FONT_LOCK = Lock()


def export_docx(output, blocks):
    document = Document()
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = section.right_margin = Cm(2.3)
    normal = document.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(12)
    for index, block in enumerate(blocks):
        paragraph = document.add_paragraph()
        if index == 0:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if index == 1:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(block)
        if index == 1:
            run.bold = True
            run.font.size = Pt(13)
    document.save(output)


def export_pdf(output, blocks):
    with FONT_LOCK:
        if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            font_path = next((path for path in FONT_PATHS if path.is_file()), None)
            if font_path is None:
                raise FileNotFoundError("Cyrillic export font is unavailable")
            pdfmetrics.registerFont(TTFont(FONT_NAME, str(font_path)))
    body = ParagraphStyle("body", fontName=FONT_NAME, fontSize=10.5, leading=15)
    address = ParagraphStyle("address", parent=body, alignment=TA_RIGHT)
    heading = ParagraphStyle("heading", parent=body, alignment=TA_CENTER, fontSize=13, leading=18)
    paragraphs = []
    for index, block in enumerate(blocks):
        style = address if index == 0 else heading if index == 1 else body
        paragraphs.append(Paragraph(escape(block).replace("\n", "<br/>"), style))
        paragraphs.append(Spacer(1, 12))
    SimpleDocTemplate(
        output, pagesize=A4, leftMargin=2.3 * cm, rightMargin=2.3 * cm, topMargin=2.3 * cm
    ).build(paragraphs)


def render_document(content, extension):
    output = BytesIO()
    blocks = content.strip().split("\n\n")
    if extension == "docx":
        export_docx(output, blocks)
    else:
        export_pdf(output, blocks)
    output.seek(0)
    return output
