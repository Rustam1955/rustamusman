"""Сообщить поисковикам, что страницы сайта появились или изменились.

IndexNow — общий для Яндекса, Bing и ещё нескольких поисковиков способ
сказать «зайди, тут новое», не дожидаясь, пока робот наткнётся сам. Кто сообщает
— подтверждается ключом: тот же ключ сайт отдаёт по адресу /<ключ>.txt (его
выдаёт Caddy облака, handle в Caddyfile). Ключ не секрет — он и так виден всем.

Google IndexNow не принимает: ему — карта сайта через Search Console.

Запуск:  python tools/indexnow_ping.py            — все страницы из sitemap.xml
         python tools/indexnow_ping.py URL ...     — только названные
"""

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

SITE = "https://ilmnur.org"
KEY = (Path(__file__).resolve().parent.parent / "data" / "indexnow_key.txt").read_text().strip()
ENGINES = (
    ("Яндекс", "https://yandex.com/indexnow"),
    ("Bing и другие", "https://api.indexnow.org/indexnow"),
)


def all_pages():
    карта = urllib.request.urlopen(f"{SITE}/sitemap.xml", timeout=20).read().decode()
    return re.findall(r"<loc>([^<]+)</loc>", карта)


def main():
    адреса = sys.argv[1:] or all_pages()
    print(f"страниц к отправке: {len(адреса)}")
    тело = json.dumps({"host": SITE.split("//")[1], "key": KEY,
                       "keyLocation": f"{SITE}/{KEY}.txt",
                       "urlList": адреса}).encode()
    for имя, адрес in ENGINES:
        запрос = urllib.request.Request(адрес, data=тело, method="POST",
                                        headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            ответ = urllib.request.urlopen(запрос, timeout=30)
            # 200 и 202 — принято; 202 значит «ключ ещё проверяем, но записали»
            print(f"  {имя}: принято ({ответ.status})")
        except urllib.error.HTTPError as беда:
            print(f"  {имя}: {беда.code} {беда.read()[:200].decode(errors='replace')}")
        except OSError as беда:
            print(f"  {имя}: не дошло — {беда}")


if __name__ == "__main__":
    main()
