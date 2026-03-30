"""Shared PDF generation utilities using reportlab."""
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
import os

# Try to register a Korean-capable font (fallback to Helvetica if not available)
_FONT_NAME = 'Helvetica'
try:
    # Check common font paths
    font_paths = [
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/System/Library/Fonts/AppleSDGothicNeo.ttc',
        'C:/Windows/Fonts/malgun.ttf',
        'C:/Windows/Fonts/gulim.ttc',
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            pdfmetrics.registerFont(TTFont('Korean', fp))
            _FONT_NAME = 'Korean'
            break
except Exception:
    pass


def make_styles():
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle', fontName=_FONT_NAME, fontSize=16, alignment=TA_CENTER,
        spaceAfter=6, textColor=colors.HexColor('#1e293b')
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle', fontName=_FONT_NAME, fontSize=10, alignment=TA_CENTER,
        spaceAfter=12, textColor=colors.HexColor('#64748b')
    )
    label_style = ParagraphStyle(
        'Label', fontName=_FONT_NAME, fontSize=9,
        textColor=colors.HexColor('#374151')
    )
    return title_style, subtitle_style, label_style


def header_table_style():
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
        ('FONTNAME',   (0, 0), (-1, -1), _FONT_NAME),
        ('FONTSIZE',   (0, 0), (-1, 0), 9),
        ('FONTSIZE',   (0, 1), (-1, -1), 8),
        ('ALIGN',      (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN',      (2, 1), (-1, -1), 'RIGHT'),
        ('GRID',       (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
    ])


def build_pdf(elements) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    doc.build(elements)
    return buf.getvalue()
