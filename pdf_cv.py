"""Генерация CV в PDF (reportlab). Кириллица через шрифт DejaVuSans."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
ACCENT = colors.HexColor("#2f5eff")
MUTED = colors.HexColor("#5b6472")

_FONTS_READY = False


def _ensure_fonts():
    global _FONTS_READY
    if _FONTS_READY:
        return
    pdfmetrics.registerFont(TTFont("DejaVu", f"{FONT_DIR}/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", f"{FONT_DIR}/DejaVuSans-Bold.ttf"))
    # Семейство: чтобы <b>/<i> внутри Paragraph находили кириллические начертания.
    # Отдельного Oblique в системе нет — italic отображаем обычным DejaVu.
    pdfmetrics.registerFontFamily(
        "DejaVu", normal="DejaVu", bold="DejaVu-Bold",
        italic="DejaVu", boldItalic="DejaVu-Bold",
    )
    _FONTS_READY = True


LABELS = {
    "ru": {
        "cv": "Резюме (CV)",
        "education": "Образование",
        "areas": "Научные интересы",
        "highlights": "Ключевые результаты",
        "pubs": "Избранные публикации",
        "contact": "Контакты",
        "more": "и другие работы — см. сайт и профиль ИСТИНА",
    },
    "en": {
        "cv": "Curriculum Vitae",
        "education": "Education",
        "areas": "Research interests",
        "highlights": "Key results",
        "pubs": "Selected publications",
        "contact": "Contact",
        "more": "and other works — see the website and ISTINA profile",
    },
    "uz": {
        "cv": "Rezyume (CV)",
        "education": "Taʼlim",
        "areas": "Ilmiy qiziqishlar",
        "highlights": "Asosiy natijalar",
        "pubs": "Tanlangan nashrlar",
        "contact": "Aloqa",
        "more": "va boshqa ishlar — saytga hamda ISTINA profiliga qarang",
    },
}

DEFAULT_LANG = "ru"


def _loc(value, lang):
    """Поле вида {'ru':..,'en':..,'uz':..} -> значение нужного языка.
    Если перевода ещё нет, откатываемся на русский."""
    if isinstance(value, dict):
        return value.get(lang) or value.get(DEFAULT_LANG)
    return value


def _styles():
    return {
        "name": ParagraphStyle("name", fontName="DejaVu-Bold", fontSize=22,
                               textColor=colors.HexColor("#16181d"), leading=26),
        "tagline": ParagraphStyle("tagline", fontName="DejaVu", leading=14, fontSize=10.5,
                                  textColor=ACCENT, spaceAfter=10),
        "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=12.5, leading=15,
                             textColor=colors.HexColor("#16181d"), spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("body", fontName="DejaVu", leading=14, fontSize=10,
                              alignment=TA_LEFT, spaceAfter=4),
        "muted": ParagraphStyle("muted", fontName="DejaVu", leading=13, fontSize=9.5,
                               textColor=MUTED, spaceAfter=3),
        "item": ParagraphStyle("item", fontName="DejaVu", leading=14, fontSize=10,
                              spaceAfter=5, leftIndent=2),
    }


def build_cv_pdf(profile, pubs, lang="ru"):
    _ensure_fonts()
    lang = lang if lang in LABELS else "ru"
    L = LABELS[lang]
    S = _styles()

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=16 * mm,
        title=f"CV — {_loc(profile['name'], lang)}",
    )
    story = []

    def rule():
        story.append(Spacer(1, 2))
        story.append(HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#e6e8ec")))
        story.append(Spacer(1, 2))

    # Шапка
    story.append(Paragraph(_loc(profile["name"], lang), S["name"]))
    story.append(Paragraph(_loc(profile["tagline"], lang), S["tagline"]))
    story.append(Paragraph(
        f'{L["contact"]}: {profile["email"]} · ISTINA: {profile["links"]["istina"]}',
        S["muted"]))
    rule()

    # Био
    for para in _loc(profile["bio"], lang):
        story.append(Paragraph(para, S["body"]))

    # Образование
    story.append(Paragraph(L["education"], S["h2"]))
    for e in profile["cv"]["education"]:
        story.append(Paragraph(f'<b>{e["period"]}</b> — {_loc(e, lang)}', S["item"]))

    # Научные интересы
    story.append(Paragraph(L["areas"], S["h2"]))
    story.append(Paragraph(" · ".join(_loc(profile["cv"]["research_areas"], lang)), S["body"]))

    # Ключевые результаты
    story.append(Paragraph(L["highlights"], S["h2"]))
    for h in _loc(profile["cv"]["highlights"], lang):
        story.append(Paragraph(f"• {h}", S["item"]))

    # Избранные публикации (до 10 последних)
    story.append(Paragraph(L["pubs"], S["h2"]))
    selected = [p for p in pubs if p.get("type") in ("article", "patent")][:10]
    for p in selected:
        authors = ", ".join(p.get("authors") or [])
        src = p.get("journal") or p.get("number") or ""
        line = f'<b>{p.get("year","")}</b>. {p["title"]}.'
        if src:
            line += f' <i>{src}</i>.'
        if p.get("doi"):
            line += f' DOI: {p["doi"]}'
        story.append(Paragraph(line, S["muted"]))
    story.append(Paragraph(L["more"], S["muted"]))

    doc.build(story)
    buf.seek(0)
    return buf.read()
