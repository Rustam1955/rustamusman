"""Выгрузка всех текстов сайта для перевода: data/i18n/source.json.

Каждый переводимый кусок — под своей меткой, с русским оригиналом и
английским вариантом для сверки. Переводчик возвращает data/i18n/<код>.json
вида {метка: перевод}; tools/i18n_merge.py вливает переводы обратно.

Метки:
  profile:/путь   — место в data/profile.json   (строка или список абзацев)
  article:/путь   — место в data/articles.json
  ui:<ключ>       — подпись интерфейса (UI в app.py)
  type:<вид>      — название вида публикации (статья, патент…)
  cv:<ключ>       — подпись в резюме PDF (pdf_cv.LABELS)
  seo             — ключевые слова для поисковиков
  alumni          — название МГУ для поисковиков (schema.org)
"""
import json, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
import app, pdf_cv  # noqa: E402

LANGS = {"ru", "en", "uz"}
items = {}


def walk(x, path, prefix):
    if isinstance(x, dict):
        if "ru" in x and set(x) <= LANGS:
            items[f"{prefix}:{path}"] = {"ru": x["ru"], "en": x.get("en", x["ru"])}
            return
        for k, v in x.items():
            walk(v, f"{path}/{k}", prefix)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            walk(v, f"{path}/{i}", prefix)


walk(json.loads((BASE / "data/profile.json").read_text(encoding="utf-8")), "", "profile")
walk(json.loads((BASE / "data/articles.json").read_text(encoding="utf-8")), "", "article")
for key, ru in app.UI["ru"].items():
    items[f"ui:{key}"] = {"ru": ru, "en": app.UI["en"].get(key, ru)}
types = {}
for p in json.loads((BASE / "data/publications.json").read_text(encoding="utf-8")):
    types.setdefault(p["type"], {"ru": p.get("type_ru", ""), "en": p.get("type_en", p.get("type_ru", ""))})
for t, v in types.items():
    items[f"type:{t}"] = v
for key, ru in pdf_cv.LABELS["ru"].items():
    items[f"cv:{key}"] = {"ru": ru, "en": pdf_cv.LABELS["en"].get(key, ru)}
items["seo"] = {"ru": app.SEO_KEYWORDS["ru"], "en": app.SEO_KEYWORDS["en"]}
items["alumni"] = {"ru": "МГУ имени М.В. Ломоносова", "en": "Lomonosov Moscow State University"}

out = BASE / "data/i18n/source.json"
out.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
chars = sum(len(json.dumps(v["ru"], ensure_ascii=False)) for v in items.values())
print(f"меток {len(items)}, русского текста {chars} знаков -> {out}")
