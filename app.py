"""
Персональный научный сайт — Усманов Рустамжон.
Flask-приложение, двуязычие RU/EN, данные из data/*.json.

Локальный запуск:
    .venv/bin/python app.py
    -> http://127.0.0.1:5000
"""
import json
import os
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from flask import (
    Flask,
    Response,
    abort,
    redirect,
    render_template,
    request,
    url_for,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__)

LANGS = ("ru", "en")
DEFAULT_LANG = "ru"

# Базовый адрес сайта (для canonical, Open Graph, sitemap).
# Можно переопределить переменной окружения SITE_URL.
SITE_URL = os.environ.get("SITE_URL", "https://rustamusman.com").rstrip("/")

# Ключевые слова для мета-тега keywords (под запросы, по которым ищут).
SEO_KEYWORDS = {
    "ru": (
        "Усманов Рустамжон, Рустамжон Усманов, Rustamzhon Usmanov, "
        "механика жидкости и газа, механика жидкости газа и плазмы, "
        "добыча урана технология, геотехнология добычи полезных ископаемых, "
        "прикладная математика, численное моделирование, научные публикации, МГУ"
    ),
    "en": (
        "Rustamzhon Usmanov, Usmanov Rustamzhon, "
        "fluid and gas mechanics, fluid gas and plasma mechanics, "
        "uranium mining technology, geotechnology of mineral extraction, "
        "applied mathematics, numerical modeling, research publications, "
        "Moscow State University"
    ),
}

# ---- Тексты интерфейса -------------------------------------------------
UI = {
    "ru": {
        "nav_home": "Главная",
        "nav_about": "О себе",
        "nav_dynasty": "Научная династия",
        "nav_pubs": "Публикации",
        "nav_cv": "CV",
        "nav_reflections": "Размышления",
        "nav_reviews": "Отзывы",
        "nav_contacts": "Контакты",
        "reflections_title": "Размышления",
        "hero_cta_pubs": "Публикации",
        "hero_cta_about": "Обо мне",
        "about_title": "О себе",
        "dynasty_title": "Научная династия и признание",
        "dynasty_sub_grandfather": "Мой дед — Ильмнур Миндияров",
        "dynasty_sub_mother": "Моя мама",
        "dynasty_sub_lineage": "История нашего рода",
        "dynasty_sub_story": "История одного спасения",
        "dynasty_sub_teachers": "Мои учителя",
        "pubs_title": "Публикации и патенты",
        "pubs_all": "Все",
        "pubs_year": "Год",
        "pubs_type": "Тип",
        "pubs_search": "Поиск по названию…",
        "pubs_open": "Открыть на ИСТИНА",
        "pubs_source": "Источник",
        "pubs_pdf": "Скачать PDF",
        "pubs_read_full": "Читать полностью",
        "pubs_none": "Ничего не найдено",
        "pubs_export": "Скачать BibTeX",
        "pubs_sort": "Сортировка",
        "sort_year_desc": "Год — новые",
        "sort_year_asc": "Год — старые",
        "sort_type": "По типу",
        "sort_journal": "По журналу",
        "pubs_authors": "Авторы",
        "cv_title": "CV — резюме",
        "cv_download": "Скачать CV (PDF)",
        "cv_education": "Образование",
        "cv_areas": "Научные интересы",
        "cv_highlights": "Ключевые результаты",
        "contacts_title": "Контакты",
        "contacts_email": "Электронная почта",
        "contacts_profiles": "Научные профили",
        "ranked": "Журнал из списка RSCI / Web of Science / Scopus",
        "stat_pubs": "публикаций",
        "footer": "Личный научный сайт",
    },
    "en": {
        "nav_home": "Home",
        "nav_about": "About",
        "nav_dynasty": "Scientific dynasty",
        "nav_pubs": "Publications",
        "nav_cv": "CV",
        "nav_reflections": "Reflections",
        "nav_reviews": "Reviews",
        "nav_contacts": "Contact",
        "reflections_title": "Reflections",
        "hero_cta_pubs": "Publications",
        "hero_cta_about": "About me",
        "about_title": "About",
        "dynasty_title": "Scientific dynasty and recognition",
        "dynasty_sub_grandfather": "My grandfather — Ilmnur Mindiyarov",
        "dynasty_sub_mother": "My mother",
        "dynasty_sub_lineage": "The story of our family",
        "dynasty_sub_story": "The story of one rescue",
        "dynasty_sub_teachers": "My teachers",
        "pubs_title": "Publications and patents",
        "pubs_all": "All",
        "pubs_year": "Year",
        "pubs_type": "Type",
        "pubs_search": "Search by title…",
        "pubs_open": "Open on ISTINA",
        "pubs_source": "Source",
        "pubs_pdf": "Download PDF",
        "pubs_read_full": "Read in full",
        "pubs_none": "Nothing found",
        "pubs_export": "Download BibTeX",
        "pubs_sort": "Sort",
        "sort_year_desc": "Year — newest",
        "sort_year_asc": "Year — oldest",
        "sort_type": "By type",
        "sort_journal": "By journal",
        "pubs_authors": "Authors",
        "cv_title": "CV — résumé",
        "cv_download": "Download CV (PDF)",
        "cv_education": "Education",
        "cv_areas": "Research interests",
        "cv_highlights": "Key results",
        "contacts_title": "Contact",
        "contacts_email": "Email",
        "contacts_profiles": "Research profiles",
        "ranked": "Journal indexed in RSCI / Web of Science / Scopus",
        "stat_pubs": "publications",
        "footer": "Personal research website",
    },
}


def load_json(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def get_profile():
    return load_json("profile.json")


def get_publications():
    path = DATA_DIR / "publications.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def get_articles():
    """Полные тексты статей: {slug: {title, year, authors, blocks, ...}}."""
    path = DATA_DIR / "articles.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def valid_lang(lang):
    return lang if lang in LANGS else DEFAULT_LANG


def build_person_jsonld(profile, lang):
    """Структурированные данные schema.org/Person — помогают поисковикам
    показать корректную карточку по запросу имени."""
    links = profile.get("links", {})
    same_as = [v for v in links.values() if str(v).startswith("http")]
    name = profile["name"]
    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": name.get(lang) or name.get(DEFAULT_LANG),
        "alternateName": [name.get("ru"), name.get("en")],
        "url": SITE_URL + f"/{lang}/",
        "image": SITE_URL + url_for("static", filename=profile.get("photo", "img/photo.jpg")),
        "email": profile.get("email"),
        "jobTitle": profile.get("tagline", {}).get(lang),
        "description": profile.get("tagline", {}).get(lang),
        "knowsAbout": profile.get("cv", {}).get("research_areas", {}).get(lang, []),
        "alumniOf": {
            "@type": "CollegeOrUniversity",
            "name": "Lomonosov Moscow State University"
            if lang == "en"
            else "МГУ имени М.В. Ломоносова",
        },
        "sameAs": same_as,
    }
    return json.dumps(data, ensure_ascii=False)


@app.context_processor
def inject_globals():
    lang = valid_lang(request.view_args.get("lang") if request.view_args else None)
    profile = get_profile()

    # canonical и языковые альтернативы (hreflang) для текущей страницы
    endpoint = request.endpoint
    canonical = SITE_URL + request.path
    alternates = {}
    # Относительные ссылки для переключателя языка: на страницах с параметрами
    # (например, статья со slug) одного lang в url_for недостаточно.
    lang_urls = {}
    if endpoint and request.view_args and "lang" in request.view_args:
        for l in LANGS:
            try:
                path = url_for(endpoint, **{**request.view_args, "lang": l})
                lang_urls[l] = path
                alternates[l] = SITE_URL + path
            except Exception:
                pass

    return {
        "lang": lang,
        "langs": LANGS,
        "t": UI[lang],
        "profile": profile,
        "current_endpoint": endpoint,
        "site_url": SITE_URL,
        "canonical": canonical,
        "alternates": alternates,
        "lang_urls": lang_urls,
        "meta_keywords": SEO_KEYWORDS[lang],
        "person_jsonld": build_person_jsonld(profile, lang),
    }


@app.route("/")
def root():
    return redirect(url_for("home", lang=DEFAULT_LANG))


@app.route("/<lang>/")
def home(lang):
    lang = valid_lang(lang)
    pubs = get_publications()
    counts = Counter(p["type"] for p in pubs)
    return render_template(
        "index.html",
        lang=lang,
        publications=pubs,
        pub_count=len(pubs),
        counts=counts,
        recent=pubs[:4],
    )


@app.route("/<lang>/about/")
def about(lang):
    return render_template("about.html", lang=valid_lang(lang))


@app.route("/<lang>/dynasty/")
def dynasty(lang):
    return render_template("dynasty.html", lang=valid_lang(lang))


@app.route("/<lang>/publications/")
def publications(lang):
    lang = valid_lang(lang)
    pubs = get_publications()
    years = sorted({p["year"] for p in pubs if p["year"]}, reverse=True)
    # типы в порядке появления
    types = []
    seen = set()
    for p in pubs:
        if p["type"] not in seen:
            seen.add(p["type"])
            types.append({"key": p["type"], "ru": p["type_ru"], "en": p["type_en"]})
    return render_template(
        "publications.html",
        lang=lang,
        publications=pubs,
        years=years,
        types=types,
    )


@app.route("/<lang>/publications/<slug>/")
def article(lang, slug):
    lang = valid_lang(lang)
    art = get_articles().get(slug)
    if art is None:
        abort(404)
    return render_template("article.html", lang=lang, article=art, slug=slug)


BIBTEX_TYPES = {
    "article": "article",
    "proceedings": "inproceedings",
    "thesis": "inproceedings",
    "dissertation": "phdthesis",
    "patent": "patent",
    "report": "techreport",
    "talk": "misc",
}


def _bib_key(pub, idx):
    """Ключ цитирования вида usmanov2025."""
    first_author = (pub.get("authors") or ["usmanov"])[0]
    surname = re.sub(r"[^A-Za-zА-Яа-я]", "", first_author.split()[0]) or "ref"
    return f"{surname}{pub.get('year') or 'nd'}{idx}"


def _bib_escape(value):
    return (value or "").replace("{", "").replace("}", "").replace("\\", "")


def make_bibtex(pubs):
    entries = []
    for i, p in enumerate(pubs, 1):
        etype = BIBTEX_TYPES.get(p.get("type"), "misc")
        fields = {
            "title": _bib_escape(p.get("title")),
            "author": _bib_escape(" and ".join(p.get("authors") or [])),
            "year": p.get("year") or "",
            "journal": _bib_escape(p.get("journal")) if etype == "article" else "",
            "booktitle": _bib_escape(p.get("journal")) if etype == "inproceedings" else "",
            "doi": p.get("doi") or "",
            "url": p.get("source_url") or p.get("url") or "",
        }
        body = ",\n".join(
            f"  {k} = {{{v}}}" for k, v in fields.items() if v
        )
        entries.append(f"@{etype}{{{_bib_key(p, i)},\n{body}\n}}")
    return "\n\n".join(entries) + "\n"


@app.route("/<lang>/publications/export.bib")
def export_bibtex(lang):
    bib = make_bibtex(get_publications())
    return Response(
        bib,
        mimetype="application/x-bibtex",
        headers={"Content-Disposition": "attachment; filename=usmanov-publications.bib"},
    )


@app.route("/<lang>/reflections/")
def reflections(lang):
    return render_template("reflections.html", lang=valid_lang(lang))


@app.route("/<lang>/cv/")
def cv(lang):
    return render_template("cv.html", lang=valid_lang(lang))


@app.route("/<lang>/reviews/")
def reviews(lang):
    return render_template("reviews.html", lang=valid_lang(lang))


@app.route("/<lang>/cv/download.pdf")
def cv_pdf(lang):
    from pdf_cv import build_cv_pdf

    lang = valid_lang(lang)
    pdf = build_cv_pdf(get_profile(), get_publications(), lang)
    # ASCII-имя для совместимости + UTF-8 (RFC 5987) для отображаемого имени
    ascii_name = "Usmanov-CV.pdf"
    utf8_name = quote("Усманов-CV.pdf" if lang == "ru" else "Usmanov-CV.pdf")
    disposition = (
        f"attachment; filename={ascii_name}; filename*=UTF-8''{utf8_name}"
    )
    return Response(
        pdf,
        mimetype="application/pdf",
        headers={"Content-Disposition": disposition},
    )


@app.route("/<lang>/contacts/")
def contacts(lang):
    return render_template("contacts.html", lang=valid_lang(lang))


@app.route("/robots.txt")
def robots_txt():
    body = f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n"
    return Response(body, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    pages = ("home", "about", "dynasty", "publications", "reflections", "cv", "reviews", "contacts")
    entries = [(endpoint, {}) for endpoint in pages]
    entries += [("article", {"slug": slug}) for slug in get_articles()]
    urls = []
    for endpoint, params in entries:
        for l in LANGS:
            loc = SITE_URL + url_for(endpoint, lang=l, **params)
            alts = "".join(
                f'<xhtml:link rel="alternate" hreflang="{a}" '
                f'href="{SITE_URL + url_for(endpoint, lang=a, **params)}"/>'
                for a in LANGS
            )
            urls.append(f"<url><loc>{loc}</loc>{alts}</url>")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">'
        + "".join(urls)
        + "</urlset>"
    )
    return Response(xml, mimetype="application/xml")


@app.template_filter("localized")
def localized(value, lang):
    """Взять поле по языку: dict {'ru':..,'en':..} -> строка."""
    if isinstance(value, dict):
        return value.get(lang) or value.get(DEFAULT_LANG) or ""
    return value


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
