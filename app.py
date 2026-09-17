"""
Персональный научный сайт — Усманов Рустамжон.
Flask-приложение, три языка RU/EN/UZ, данные из data/*.json.

Локальный запуск:
    .venv/bin/python app.py
    -> http://127.0.0.1:5000
"""
import datetime
import io
import json
import os
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import qrcode
import qrcode.image.svg

from flask import (
    Flask,
    Response,
    abort,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.middleware.proxy_fix import ProxyFix

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__)
# В облаке сайт стоит за Caddy: без этого Flask считает запрос http и шлёт
# переадресации вида http://ilmnur.org/ru/. Верим одному посреднику —
# gunicorn слушает только 127.0.0.1, так что заголовки ставит лишь Caddy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# С 16.09.2026 — все 20 языков приложения IlmNur (Рустам: «мы же договорились
# на 20 языках»). Тексты ru/en/uz лежат в самих данных, остальные — переводы
# из data/i18n/<код>.json (выгрузку делает tools/i18n_extract.py), их
# накладываем при загрузке. Чего в переводе нет — по-английски (Рустам: «где
# невозможно перевод, оставь текст на английском»)
LANGS = ("ru", "en", "uz", "ar", "be", "de", "es", "fa", "fr", "he", "hi",
         "it", "ja", "kk", "ko", "pl", "pt", "tg", "tr", "zh")
DEFAULT_LANG = "ru"
FALLBACK_LANG = "en"
# Пишутся справа налево: <html dir="rtl">, стороны в стилях — логические
RTL_LANGS = {"ar", "fa", "he"}
# Шрифт DejaVu в резюме PDF знает латиницу и кириллицу; арабское письмо,
# иврит, деванагари и иероглифы не нарисует — там резюме по-английски
PDF_LANGS = set(LANGS) - {"ar", "fa", "he", "hi", "ja", "ko", "zh"}
I18N_DIR = DATA_DIR / "i18n"
# Как языки называют себя в меню настроек — те же слова, что в приложении
# IlmNur (lang_name в его словарях SETUP_APP/locales), рядом с тем же флагом
LANG_NAMES = {
    "ru": "Русский", "en": "English", "uz": "Oʻzbekcha", "ar": "العربية",
    "be": "Беларуская", "de": "Deutsch", "es": "Español", "fa": "فارسی",
    "fr": "Français", "he": "עברית", "hi": "हिन्दी", "it": "Italiano",
    "ja": "日本語", "kk": "Қазақ тілі", "ko": "한국어", "pl": "Polski",
    "pt": "Português", "tg": "Тоҷикӣ", "tr": "Türkçe", "zh": "中文",
}

# Узбекский — латиница (uz-Latn): для hreflang и og:locale нужен полный код.
LOCALES = {"ru": "ru_RU", "en": "en_US", "uz": "uz_Latn_UZ", "ar": "ar_AR",
           "be": "be_BY", "de": "de_DE", "es": "es_ES", "fa": "fa_IR",
           "fr": "fr_FR", "he": "he_IL", "hi": "hi_IN", "it": "it_IT",
           "ja": "ja_JP", "kk": "kk_KZ", "ko": "ko_KR", "pl": "pl_PL",
           "pt": "pt_BR", "tg": "tg_TJ", "tr": "tr_TR", "zh": "zh_CN"}
HREFLANG = {l: l for l in LANGS} | {"uz": "uz-Latn", "zh": "zh-Hans"}

# Базовый адрес сайта (для canonical, Open Graph, sitemap).
# Можно переопределить переменной окружения SITE_URL. С 16.09.2026 сайт
# живёт на ilmnur.org, в облаке вместе с IlmNur (раньше — rustamusman.com)
SITE_URL = os.environ.get("SITE_URL", "https://ilmnur.org").rstrip("/")

# Ключевые слова для мета-тега keywords (под запросы, по которым ищут).
SEO_KEYWORDS = {
    "ru": (
        "Усманов Рустамжон, Рустамжон Усманов, Усманов Рустамжон Исаевич, "
        "Усманов Р.И., Rustamzhon Usmanov, Usmanov Rustamjon, "
        "механика жидкости и газа, механика жидкости газа и плазмы, "
        "добыча урана технология, геотехнология добычи полезных ископаемых, "
        "прикладная математика, численное моделирование, научные публикации, МГУ, "
        "золото, уран, редкоземельные металлы, "
        "лауреат Государственной премии в области науки и техники, лауреат Государственной премии Республики Узбекистан"
    ),
    "en": (
        "Rustamzhon Usmanov, Usmanov Rustamzhon, Usmanov Rustamjon, "
        "fluid and gas mechanics, fluid gas and plasma mechanics, "
        "uranium mining technology, geotechnology of mineral extraction, "
        "applied mathematics, numerical modeling, research publications, "
        "Moscow State University, "
        "gold, uranium, rare earth metals, Усманов Рустамжон, "
        "laureate of the State Prize in science and technology, State Prize of the Republic of Uzbekistan"
    ),
    "uz": (
        "Usmanov Rustamjon, Rustamjon Usmanov, Usmanov Rustamjon Isayevich, "
        "Usmanov R.I., Rustamzhon Usmanov, "
        "suyuqlik va gaz mexanikasi, suyuqlik, gaz va plazma mexanikasi, "
        "uran qazib olish texnologiyasi, foydali qazilmalarni qazib olish "
        "geotexnologiyasi, yer osti ishqorlash, amaliy matematika, "
        "sonli modellashtirish, ilmiy nashrlar, MDU, "
        "oltin, uran, noyob yer metallari, Усманов Рустамжон, "
        "fan va texnika sohasidagi Davlat mukofoti sovrindori, Oʻzbekiston Respublikasi Davlat mukofoti"
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
        "nav_appendix": "Приложения",
        "nav_reflections": "Размышления",
        "nav_reviews": "Отзывы",
        "nav_contacts": "Контакты",
        "settings_title": "Настройки",
        "set_lang": "Язык",
        "set_theme": "Тема",
        "theme_day": "День",
        "theme_night": "Ночь",
        "set_bg": "Фон экрана",
        "bg_glow": "Сияние",
        "bg_photo": "Фото",
        "bg_plain": "Без фона",
        "set_back": "Назад",
        "reflections_title": "Размышления",
        "appendix_title": "Приложения",
        "appendix_app_name": "IlmNur",
        "appendix_app_desc": "Семейное приложение: родословная, шахматы, музыка и разговор со звуком — на телефоне и на компьютере, на двадцати языках.",
        "appendix_named": "Названо в честь моего деда — Илмнура Миндиярова.",
        "appendix_android": "Приложение для Android",
        "appendix_scan": "Наведите камеру телефона на код — приложение скачается само.",
        "appendix_download": "Скачать для Android",
        "appendix_talk": "Разговор",
        "appendix_talk_desc": "Разговор со звуком прямо в браузере — до восьми человек.",
        "appendix_talk_enter": "Войти в разговор",
        "appendix_login": "Вход — по своей учётной записи IlmNur; новую учётную запись одобряет администратор.",
        "hero_cta_pubs": "Публикации",
        "hero_cta_about": "Обо мне",
        "about_title": "О себе",
        "dynasty_title": "Научная династия и признание",
        "dynasty_sub_grandfather": "Мой дед — Илмнур Миндияров",
        "dynasty_sub_mother": "Моя мама",
        "dynasty_sub_lineage": "История нашего рода",
        "dynasty_sub_silence": "Сквозь боль и молчание",
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
        "stat_patents": "патентов",
        "stat_dissertations": "диссертации",
        "stat_years": "лет в науке",
        "cert": "Свидетельство",
        "ilmnur_alt": "Ilm Nur — свет знаний и чистота души",
        "home_title_tag": "добыча урана, золота и редкоземельных металлов",
        "home_meta_desc": (
            "Официальный сайт учёного Рустамжона Усманова (Усманов Рустамжон): "
            "механика жидкости, газа и плазмы, технологии добычи урана, золота и "
            "редкоземельных металлов, геотехнология добычи полезных ископаемых. "
            "Публикации, патенты, CV."
        ),
        # Подвал — одной фразой, имя внутри (Рустам, 16.09.2026)
        "footer": "Личный научный сайт «IlmNur» Усманова Р.",
    },
    "en": {
        "nav_home": "Home",
        "nav_about": "About",
        "nav_dynasty": "Scientific dynasty",
        "nav_pubs": "Publications",
        "nav_cv": "CV",
        # Раздел — приложение IlmNur, а не «приложения к книге» (16.09.2026)
        "nav_appendix": "Apps",
        "nav_reflections": "Reflections",
        "nav_reviews": "Reviews",
        "nav_contacts": "Contact",
        "settings_title": "Settings",
        "set_lang": "Language",
        "set_theme": "Theme",
        "theme_day": "Day",
        "theme_night": "Night",
        "set_bg": "Background",
        "bg_glow": "Glow",
        "bg_photo": "Photo",
        "bg_plain": "Plain",
        "set_back": "Back",
        "reflections_title": "Reflections",
        "appendix_title": "Apps",
        "appendix_app_name": "IlmNur",
        "appendix_app_desc": "A family app: family tree, chess, music and voice talk — on the phone and the computer, in twenty languages.",
        "appendix_named": "Named after my grandfather, Ilmnur Mindiyarov.",
        "appendix_android": "App for Android",
        "appendix_scan": "Point your phone camera at the code — the app will download.",
        "appendix_download": "Download for Android",
        "appendix_talk": "Voice talk",
        "appendix_talk_desc": "Voice conversation right in the browser — up to eight people.",
        "appendix_talk_enter": "Join the talk",
        "appendix_login": "Sign in with your IlmNur account; new accounts are approved by the administrator.",
        "hero_cta_pubs": "Publications",
        "hero_cta_about": "About me",
        "about_title": "About",
        "dynasty_title": "Scientific dynasty and recognition",
        "dynasty_sub_grandfather": "My grandfather — Ilmnur Mindiyarov",
        "dynasty_sub_mother": "My mother",
        "dynasty_sub_lineage": "The story of our family",
        "dynasty_sub_silence": "Through pain and silence",
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
        "stat_patents": "patents",
        "stat_dissertations": "dissertations",
        "stat_years": "years in science",
        "cert": "Certificate",
        "ilmnur_alt": "Ilm Nur — the light of knowledge and purity of the soul",
        "home_title_tag": "uranium, gold and rare earth metals extraction",
        "home_meta_desc": (
            "Official website of scientist Rustamzhon Usmanov (Usmanov Rustamjon): "
            "fluid, gas and plasma mechanics, technologies for extracting uranium, "
            "gold and rare earth metals, geotechnology of mineral extraction. "
            "Publications, patents and CV."
        ),
        "footer": "«IlmNur» — personal research website of R. Usmanov",
    },
    "uz": {
        "nav_home": "Bosh sahifa",
        "nav_about": "Men haqimda",
        "nav_dynasty": "Ilmiy sulola",
        "nav_pubs": "Nashrlar",
        "nav_cv": "CV",
        "nav_appendix": "Ilovalar",
        "nav_reflections": "Mulohazalar",
        "nav_reviews": "Taqrizlar",
        "nav_contacts": "Aloqa",
        "settings_title": "Sozlamalar",
        "set_lang": "Til",
        "set_theme": "Mavzu",
        "theme_day": "Kunduz",
        "theme_night": "Tun",
        "set_bg": "Ekran foni",
        "bg_glow": "Nur",
        "bg_photo": "Foto",
        "bg_plain": "Fonsiz",
        "set_back": "Orqaga",
        "reflections_title": "Mulohazalar",
        "appendix_title": "Ilovalar",
        "appendix_app_name": "IlmNur",
        "appendix_app_desc": "Oilaviy ilova: shajara, shaxmat, musiqa va ovozli suhbat — telefonda va kompyuterda, yigirmata tilda.",
        "appendix_named": "Bobom — Ilmnur Mindiyarov sharafiga nomlangan.",
        "appendix_android": "Android uchun ilova",
        "appendix_scan": "Telefon kamerasini kodga qarating — ilova oʻzi yuklab olinadi.",
        "appendix_download": "Android uchun yuklab olish",
        "appendix_talk": "Suhbat",
        "appendix_talk_desc": "Toʻgʻridan-toʻgʻri brauzerda ovozli suhbat — sakkiz kishigacha.",
        "appendix_talk_enter": "Suhbatga kirish",
        "appendix_login": "Kirish — oʻzingizning IlmNur hisobingiz orqali; yangi hisobni administrator tasdiqlaydi.",
        "hero_cta_pubs": "Nashrlar",
        "hero_cta_about": "Men haqimda",
        "about_title": "Men haqimda",
        "dynasty_title": "Ilmiy sulola va eʼtirof",
        "dynasty_sub_grandfather": "Bobom — Ilmnur Mindiyarov",
        "dynasty_sub_mother": "Onam",
        "dynasty_sub_lineage": "Naslimiz tarixi",
        "dynasty_sub_silence": "Ogʻriq va sukunat orqali",
        "dynasty_sub_story": "Bir najot qissasi",
        "dynasty_sub_teachers": "Ustozlarim",
        "pubs_title": "Nashrlar va patentlar",
        "pubs_all": "Barchasi",
        "pubs_year": "Yil",
        "pubs_type": "Turi",
        "pubs_search": "Nomi boʻyicha qidirish…",
        "pubs_open": "ISTINA saytida ochish",
        "pubs_source": "Manba",
        "pubs_pdf": "PDF yuklab olish",
        "pubs_read_full": "Toʻliq oʻqish",
        "pubs_none": "Hech narsa topilmadi",
        "pubs_export": "BibTeX yuklab olish",
        "pubs_sort": "Saralash",
        "sort_year_desc": "Yil — yangilari",
        "sort_year_asc": "Yil — eskilari",
        "sort_type": "Turi boʻyicha",
        "sort_journal": "Jurnal boʻyicha",
        "pubs_authors": "Mualliflar",
        "cv_title": "CV — rezyume",
        "cv_download": "CV yuklab olish (PDF)",
        "cv_education": "Taʼlim",
        "cv_areas": "Ilmiy qiziqishlar",
        "cv_highlights": "Asosiy natijalar",
        "contacts_title": "Aloqa",
        "contacts_email": "Elektron pochta",
        "contacts_profiles": "Ilmiy profillar",
        "ranked": "RSCI / Web of Science / Scopus roʻyxatidagi jurnal",
        "stat_pubs": "nashr",
        "stat_patents": "patent",
        "stat_dissertations": "dissertatsiya",
        "stat_years": "yil ilmda",
        "cert": "Guvohnoma",
        "ilmnur_alt": "Ilm Nur — bilim nuri va qalb pokligi",
        "home_title_tag": "uran, oltin va noyob yer metallarini qazib olish",
        "home_meta_desc": (
            "Olim Rustamjon Usmanovning rasmiy sayti: suyuqlik, gaz va plazma "
            "mexanikasi, uran, oltin va noyob yer metallarini qazib olish "
            "texnologiyalari, foydali qazilmalarni qazib olish geotexnologiyasi. "
            "Nashrlar, patentlar, CV."
        ),
        "footer": "Usmanov R.ning «IlmNur» shaxsiy ilmiy sayti",
    },
}


# ---- Переводы на 17 языков сверх ru/en/uz --------------------------------
def _load_translations():
    """{код: {метка: перевод}}; нет файла или он испорчен — пусто, и язык
    целиком идёт по-английски"""
    out = {}
    for l in LANGS:
        if l in ("ru", "en", "uz"):
            continue
        try:
            out[l] = json.loads((I18N_DIR / f"{l}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            out[l] = {}
    return out


TRANSLATIONS = _load_translations()
ALUMNI = {"ru": "МГУ имени М.В. Ломоносова",
          "en": "Lomonosov Moscow State University",
          "uz": "M.V. Lomonosov nomidagi Moskva davlat universiteti"}
for _l, _t in TRANSLATIONS.items():
    UI[_l] = {**UI[FALLBACK_LANG],
              **{k[3:]: v for k, v in _t.items() if k.startswith("ui:")}}
    SEO_KEYWORDS[_l] = _t.get("seo") or SEO_KEYWORDS[FALLBACK_LANG]
    ALUMNI[_l] = _t.get("alumni") or ALUMNI[FALLBACK_LANG]


def _overlay(data, prefix):
    """Кладёт переводы в узлы {ru, en, uz} данных: узел[код] = перевод.
    Метка вида «profile:/heritage/text» — путь от корня файла"""
    for l, t in TRANSLATIONS.items():
        for label, text in t.items():
            if not label.startswith(prefix + ":/"):
                continue
            node = data
            try:
                for part in label[len(prefix) + 2:].split("/"):
                    node = node[int(part)] if isinstance(node, list) else node[part]
            except (KeyError, IndexError, ValueError, TypeError):
                continue      # данные поменялись после выгрузки — перевод пропускаем
            if isinstance(node, dict):
                node[l] = text
    return data


def type_name(kind, lang, fallback=""):
    """Вид публикации на языке: перевод, иначе английский, иначе как есть"""
    return TRANSLATIONS.get(lang, {}).get(f"type:{kind}") or fallback


def load_json(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def get_profile():
    return _overlay(load_json("profile.json"), "profile")


def get_publications():
    path = DATA_DIR / "publications.json"
    if not path.exists():
        return []
    pubs = json.loads(path.read_text(encoding="utf-8"))
    # Подписи типа на каждом языке: перевод, иначе английский — чтобы
    # шаблоны с p['type_' + lang] не падали.
    for p in pubs:
        english = p.get("type_en") or p.get("type_ru", p.get("type", ""))
        for l in LANGS:
            p.setdefault(f"type_{l}", type_name(p.get("type"), l, english))
    return pubs


def get_articles():
    """Полные тексты статей: {slug: {title, year, authors, blocks, ...}}."""
    path = DATA_DIR / "articles.json"
    if not path.exists():
        return {}
    arts = _overlay(json.loads(path.read_text(encoding="utf-8")), "article")
    # Вида у статьи нет полем — узнаём по русской подписи из публикаций
    kinds = {p.get("type_ru"): p.get("type") for p in get_publications()}
    for a in arts.values():
        english = a.get("type_en") or a.get("type_ru", "")
        for l in LANGS:
            a.setdefault(f"type_{l}", type_name(kinds.get(a.get("type_ru")), l, english))
    return arts


def valid_lang(lang):
    return lang if lang in LANGS else DEFAULT_LANG


# Темы, по которым сайт должны находить (Рустам, 16.09.2026: «ключевые слова
# для поиска: золото, уран, редкоземельные металлы, Усманов Рустамжон,
# Usmanov Rustamjon»). Всё это правда о работах: патенты на извлечение золота,
# добыча урана, «технологии добычи редких, редкоземельных и благородных
# металлов» в биографии. Идут в карточку учёного для поисковиков (knowsAbout);
# те же слова стоят в заголовке, описании и keywords главной
SEO_TOPICS = {
    "ru": ["золото", "уран", "редкоземельные металлы"],
    "en": ["gold", "uranium", "rare earth metals"],
    "uz": ["oltin", "uran", "noyob yer metallari"],
    "ar": ["الذهب", "اليورانيوم", "المعادن الأرضية النادرة"],
    "be": ["золата", "уран", "рэдказямельныя металы"],
    "de": ["Gold", "Uran", "Seltenerdmetalle"],
    "es": ["oro", "uranio", "metales de tierras raras"],
    "fa": ["طلا", "اورانیوم", "فلزات خاکی کمیاب"],
    "fr": ["or", "uranium", "terres rares"],
    "he": ["זהב", "אורניום", "מתכות אדמה נדירות"],
    "hi": ["सोना", "यूरेनियम", "दुर्लभ मृदा धातुएँ"],
    "it": ["oro", "uranio", "terre rare"],
    "ja": ["金", "ウラン", "レアアース"],
    "kk": ["алтын", "уран", "сирек жер металдары"],
    "ko": ["금", "우라늄", "희토류"],
    "pl": ["złoto", "uran", "metale ziem rzadkich"],
    "pt": ["ouro", "urânio", "metais de terras raras"],
    "tg": ["тилло", "уран", "металлҳои нодири заминӣ"],
    "tr": ["altın", "uranyum", "nadir toprak metalleri"],
    "zh": ["金", "铀", "稀土金属"],
}
# Награда — в карточку учёного (schema.org award). Рустам, 16.09.2026: «ещё
# ключевое слово — лауреат Государственной премии в области науки и техники».
# Слово в слово как в первой строке биографии на каждом языке
SEO_AWARD = {
    "ru": "Государственная премия Республики Узбекистан первой степени в области науки и техники",
    "en": "State Prize of the Republic of Uzbekistan of the first degree in science and technology",
    "uz": "Oʻzbekiston Respublikasining fan va texnika sohasidagi birinchi darajali Davlat mukofoti",
    "ar": "جائزة الدولة لجمهورية أوزبكستان من الدرجة الأولى في مجال العلوم والتكنولوجيا",
    "be": "Дзяржаўная прэмія Рэспублікі Узбекістан першай ступені ў галіне навукі і тэхнікі",
    "de": "Staatspreis der Republik Usbekistan ersten Grades auf dem Gebiet von Wissenschaft und Technik",
    "es": "Premio Estatal de la República de Uzbekistán de primer grado en ciencia y tecnología",
    "fa": "جایزهٔ دولتی درجهٔ یک جمهوری ازبکستان در زمینهٔ علم و فناوری",
    "fr": "Prix d'État de la République d'Ouzbékistan du premier degré dans le domaine de la science et de la technique",
    "he": "פרס המדינה של הרפובליקה של אוזבקיסטן מדרגה ראשונה בתחום המדע והטכנולוגיה",
    "hi": "विज्ञान और प्रौद्योगिकी के क्षेत्र में उज़्बेकिस्तान गणराज्य का प्रथम श्रेणी का राजकीय पुरस्कार",
    "it": "Premio di Stato della Repubblica dell'Uzbekistan di primo grado nel campo della scienza e della tecnologia",
    "ja": "ウズベキスタン共和国科学技術分野国家賞（一等）",
    "kk": "Өзбекстан Республикасының ғылым және техника саласындағы бірінші дәрежелі Мемлекеттік сыйлығы",
    "ko": "우즈베키스탄 공화국 과학기술 분야 1등급 국가상",
    "pl": "Nagroda Państwowa Republiki Uzbekistanu pierwszego stopnia w dziedzinie nauki i techniki",
    "pt": "Prêmio Estatal da República do Uzbequistão de primeiro grau na área de ciência e tecnologia",
    "tg": "Мукофоти давлатии дараҷаи якуми Ҷумҳурии Ӯзбекистон дар соҳаи илм ва техника",
    "tr": "Özbekistan Cumhuriyeti Bilim ve Teknoloji Alanında Birinci Derece Devlet Ödülü",
    "zh": "乌兹别克斯坦共和国一等国家科学技术奖",
}
# Оба написания имени, которые Рустам назвал, — во всех языках
SEO_NAMES = ("Усманов Рустамжон", "Usmanov Rustamjon")


def build_person_jsonld(profile, lang):
    """Структурированные данные schema.org/Person — помогают поисковикам
    показать корректную карточку по запросу имени."""
    links = profile.get("links", {})
    same_as = [v for v in links.values() if str(v).startswith("http")]
    name = profile["name"]
    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": localized(name, lang),
        "alternateName": sorted({name.get(l) for l in LANGS if name.get(l)} | set(SEO_NAMES)),
        "url": SITE_URL + f"/{lang}/",
        "image": SITE_URL + url_for("static", filename=profile.get("photo", "img/photo.jpg")),
        "email": profile.get("email"),
        "jobTitle": localized(profile.get("tagline", {}), lang),
        "description": localized(profile.get("tagline", {}), lang),
        "knowsAbout": (localized(profile.get("cv", {}).get("research_areas", {}), lang) or [])
                      + SEO_TOPICS.get(lang, SEO_TOPICS[FALLBACK_LANG]),
        "award": SEO_AWARD.get(lang, SEO_AWARD[FALLBACK_LANG]),
        "alumniOf": {
            "@type": "CollegeOrUniversity",
            "name": ALUMNI.get(lang, ALUMNI[FALLBACK_LANG]),
        },
        "sameAs": same_as,
    }
    return json.dumps(data, ensure_ascii=False)


@app.before_request
def only_known_language():
    """Неизвестный язык в адресе — не главная страница по-русски.

    Раньше любой адрес вида /что-то/ подходил под правило /<lang>/ и
    показывал русскую главную: так отвечал даже /static/. Теперь такой адрес
    переводит на ту же страницу на языке по умолчанию (16.09.2026)"""
    язык = (request.view_args or {}).get("lang")
    if язык is None or язык in LANGS:
        return None
    try:
        куда = url_for(request.endpoint, **{**request.view_args, "lang": DEFAULT_LANG})
    except Exception:
        куда = url_for("home", lang=DEFAULT_LANG)
    return redirect(куда, code=302)


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
                alternates[HREFLANG[l]] = SITE_URL + path
            except Exception:
                pass

    return {
        "lang": lang,
        "dir": "rtl" if lang in RTL_LANGS else "ltr",
        "langs": LANGS,
        "lang_names": LANG_NAMES,
        "t": UI[lang],
        "profile": profile,
        "current_endpoint": endpoint,
        "site_url": SITE_URL,
        "canonical": canonical,
        "alternates": alternates,
        "lang_urls": lang_urls,
        "meta_keywords": SEO_KEYWORDS[lang],
        "og_locale": LOCALES[lang],
        "person_jsonld": build_person_jsonld(profile, lang),
    }


@app.route("/")
def root():
    # 301, «переехало насовсем»: поисковик переносит на /ru/ всё, что знал о
    # корне. При 302 он считал переход временным и продолжал держать в
    # выдаче сам корень, у которого своего содержимого нет (16.09.2026)
    return redirect(url_for("home", lang=DEFAULT_LANG), code=301)


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
            types.append({"key": p["type"], **{l: p[f"type_{l}"] for l in LANGS}})
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


# ---- Приложение IlmNur ---------------------------------------------------
# Сайт живёт на ilmnur.org вместе с IlmNur (16.09.2026). APK отдаёт Caddy
# облака из /var/www/ilmnur, разговор — своя служба на talk.ilmnur.org.
# Раньше здесь была кнопка запуска настольного приложения на машине сайта.
# Её убрали: в облаке окно открыть негде, а за Caddy «свой» адрес 127.0.0.1
# у всех посетителей — любой из интернета запускал бы программы на сервере
APK_URL = os.environ.get("ILMNUR_APK_URL", "https://ilmnur.org/ilmnur.apk")
TALK_URL = os.environ.get("ILMNUR_TALK_URL", "https://talk.ilmnur.org/")
# Сам файл приложения: по его времени узнаём, какая сборка сейчас выложена
APK_FILE = Path(os.environ.get("ILMNUR_APK_FILE", "/var/www/ilmnur/ilmnur.apk"))


def apk_version():
    """Отметка выложенной сборки — время файла, например «16.09.2026-0626».

    Нужна затем, что и ссылка, и QR-код должны меняться вместе с программой.
    Пока они были неизменны, телефон с чистой совестью показывал картинку,
    сохранённую у себя месяц назад, и ставил APK, скачанный тогда же
    (Рустам, 16.09.2026: «в сайте старый qr code»)"""
    try:
        когда = datetime.datetime.fromtimestamp(APK_FILE.stat().st_mtime)
        return когда.strftime("%d.%m.%Y-%H%M")
    except OSError:
        # Файла рядом нет (так бывает на домашней машине) — сборку не назовём,
        # но страница должна открыться
        return "0"


def apk_link():
    """Ссылка на APK с отметкой сборки. Для Caddy отметка — пустой звук, файл
    он отдаёт тот же; а вот браузер и «Загрузки» телефона видят новый адрес"""
    return f"{APK_URL}?v={apk_version()}"


@app.route("/apk-qr.svg")
def apk_qr():
    """QR-код на приложение — рисуется здесь и сейчас.

    Раньше это была картинка в static, нарисованная однажды рукой. Устареть
    ей было негде, но телефон держал у себя её копию и показывал прежнюю.
    Теперь код собирается на каждый заход, ведёт на нынешнюю сборку и
    просит себя не запоминать"""
    код = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    код.add_data(apk_link())
    код.make(fit=True)
    # ...Fill — с белой подложкой. Без неё код выходит прозрачным: на тёмной
    # теме сайта чёрные клетки ложились на тёмное, и кода было не видно
    # (Рустам, 16.09.2026). Телефон такой код не прочтёт и с экрана
    картинка = код.make_image(image_factory=qrcode.image.svg.SvgPathFillImage)
    лист = io.BytesIO()
    картинка.save(лист)
    return Response(лист.getvalue(), mimetype="image/svg+xml",
                    headers={"Cache-Control": "no-store, max-age=0"})


@app.route("/<lang>/appendix/")
def appendix(lang):
    return render_template(
        "appendix.html",
        lang=valid_lang(lang),
        apk_url=apk_link(),
        apk_qr_url=url_for("apk_qr", v=apk_version()),
        talk_url=TALK_URL,
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
    from pdf_cv import LABELS, build_cv_pdf

    lang = valid_lang(lang)
    # Языки, которые шрифт PDF не нарисует, — резюме по-английски (PDF_LANGS)
    pdf_lang = lang if lang in PDF_LANGS else FALLBACK_LANG
    labels = LABELS.get(pdf_lang) or {
        **LABELS[FALLBACK_LANG],
        **{k[3:]: v for k, v in TRANSLATIONS.get(pdf_lang, {}).items() if k.startswith("cv:")}}
    pdf = build_cv_pdf(get_profile(), get_publications(), pdf_lang, labels)
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
    pages = ("home", "about", "dynasty", "publications", "appendix", "reflections", "cv", "reviews", "contacts")
    entries = [(endpoint, {}) for endpoint in pages]
    entries += [("article", {"slug": slug}) for slug in get_articles()]
    urls = []
    for endpoint, params in entries:
        for l in LANGS:
            loc = SITE_URL + url_for(endpoint, lang=l, **params)
            alts = "".join(
                f'<xhtml:link rel="alternate" hreflang="{HREFLANG[a]}" '
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
    """Взять поле по языку: dict {'ru':..,'en':..,'uz':.., <переводы>} -> строка.

    Если перевода на запрошенный язык нет — по-английски (Рустам: «где
    невозможно перевод, оставь текст на английском»), нет и его — русский."""
    if isinstance(value, dict):
        return value.get(lang) or value.get(FALLBACK_LANG) or value.get(DEFAULT_LANG) or ""
    return value


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
