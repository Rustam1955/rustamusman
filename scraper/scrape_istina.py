"""
Парсер публикаций с профиля ИСТИНА МГУ.
Забирает список работ (статьи, сборники, тезисы, диссертации) и сохраняет
в data/publications.json для использования сайтом на Flask.

Запуск:  python scraper/scrape_istina.py
"""
import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")

WORKER_ID = "258800219"
BASE = "https://istina.msu.ru"
URL = f"{BASE}/workers/{WORKER_ID}/publications/"
SELF_WORKER_URL = f"/workers/{WORKER_ID}/"

# Заголовок секции ИСТИНА -> тип публикации (ключ)
SECTION_TYPES = {
    "Статьи в журналах": ("article", "Статья в журнале", "Journal article"),
    "Статьи в сборниках": ("proceedings", "Статья в сборнике", "Proceedings"),
    "Тезисы докладов": ("thesis", "Тезисы доклада", "Conference abstract"),
    "Диссертации": ("dissertation", "Диссертация", "Dissertation"),
    "Патенты": ("patent", "Патент", "Patent"),
    "Доклады на конференциях": ("talk", "Доклад", "Talk"),
    "Научные отчеты": ("report", "Научный отчёт", "Report"),
}

OUT = Path(__file__).resolve().parent.parent / "data" / "publications.json"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_item(outer_li):
    """Разобрать один <li> публикации в словарь."""
    activity = outer_li.find("ul", class_="activity")
    if not activity:
        return None

    inner = activity.find_all("li", recursive=False)
    if not inner:
        return None

    head = inner[0]
    year = activity.get("data-year")
    if not year:
        b = head.find("b")
        year = clean(b.get_text()) if b else ""
    year = year if re.fullmatch(r"\d{4}", year or "") else (year or "")

    title_a = head.find("a", href=True)
    title = clean(title_a.get_text()) if title_a else clean(head.get_text())
    url = BASE + title_a["href"] if title_a else ""

    # Авторы — из второго вложенного <li> (ссылки на сотрудников)
    authors = []
    if len(inner) > 1:
        for a in inner[1].find_all("a", href=True):
            name = clean(a.get_text())
            if name:
                authors.append(name)
    # Остаток текста (журнал, том, страницы)
    citation = ""
    if len(inner) > 1:
        citation = clean(inner[1].get_text(" ", strip=True))
        for name in authors:
            citation = citation.replace(name, "")
        citation = clean(citation.strip(" ,"))

    # Значок «звезда» = журнал из списка RSCI / Web of Science / Scopus
    star = outer_li.find("span", class_=re.compile(r"fa-star"))
    ranked = bool(star)
    rank_note = clean(star.get("title", "")) if star else ""

    return {
        "year": year,
        "title": title,
        "url": url,
        "authors": authors,
        "citation": citation,
        "ranked": ranked,
        "rank_note": rank_note,
    }


def enrich(pub, session):
    """Зайти на страницу публикации и добавить ссылки на источник: DOI,
    прямую ссылку, журнал и его страницу на ИСТИНА."""
    url = pub.get("url")
    if not url:
        return pub
    try:
        r = session.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
    except requests.RequestException as exc:
        print(f"  ! не удалось открыть {url}: {exc}")
        return pub
    soup = BeautifulSoup(r.text, "lxml")

    # DOI (из текста или из ссылки dx.doi.org)
    doi = ""
    m = DOI_RE.search(r.text)
    if m:
        doi = m.group(0).rstrip(".,;)")

    # Прямая ссылка на источник (doi.org или внешний ресурс)
    source_url = f"https://doi.org/{doi}" if doi else ""
    if not source_url:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and "istina.msu.ru" not in href:
                if any(k in href for k in ("doi.org", "elibrary", "sciencedirect",
                                           "springer", "wiley", "mdpi", "iopscience")):
                    source_url = href
                    break

    # Журнал / сборник
    journal, journal_url = "", ""
    for a in soup.find_all("a", href=True):
        if "/journals/" in a["href"] or "/collections/" in a["href"]:
            journal = clean(a.get_text())
            journal_url = BASE + a["href"]
            break

    pub["doi"] = doi
    pub["source_url"] = source_url
    pub["journal"] = journal
    pub["journal_url"] = journal_url
    return pub


def main():
    headers = HEADERS
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    publications = []
    for header in soup.find_all(["h2", "h3"]):
        sec_title = clean(header.get_text())
        if sec_title not in SECTION_TYPES:
            continue
        type_key, type_ru, type_en = SECTION_TYPES[sec_title]
        lst = header.find_next(["ol", "ul"])
        if not lst:
            continue
        for li in lst.find_all("li", recursive=False):
            item = parse_item(li)
            if not item or not item["title"]:
                continue
            item.update(type=type_key, type_ru=type_ru, type_en=type_en)
            publications.append(item)

    # Второй проход: обогащаем каждую работу ссылками на источник
    print(f"Найдено {len(publications)} работ, собираю ссылки на источники…")
    with requests.Session() as session:
        for i, pub in enumerate(publications, 1):
            enrich(pub, session)
            src = "DOI" if pub.get("doi") else ("источник" if pub.get("source_url") else "—")
            print(f"  [{i}/{len(publications)}] {pub['year']} {src}  {pub['title'][:55]}")
            time.sleep(0.4)  # вежливая пауза между запросами

    # Сортировка: новые сверху
    publications.sort(key=lambda p: (p["year"] or "0"), reverse=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(publications, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Сводка по типам
    counts = {}
    for p in publications:
        counts[p["type_ru"]] = counts.get(p["type_ru"], 0) + 1
    print(f"Сохранено {len(publications)} публикаций -> {OUT}")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
