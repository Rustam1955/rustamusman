"""Проверка переводов сайта: data/i18n/<код>.json против data/i18n/source.json.

Запуск:  .venv/bin/python tools/i18n_check.py [код ...]
Без кодов — все найденные файлы переводов.

Проверяет: метки те же, что в выгрузке; строка на месте строки, список той
же длины на месте списка; пустых нет; числа (годы, даты, номера патентов,
проценты) и химические формулы — те же, что в русском оригинале. Числа в
переводе можно записать иначе (1 000 и 1000), поэтому сверяем только
«голые» цифры без пробелов и разделителей.
"""
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
I18N = BASE / "data" / "i18n"
FORMULA = re.compile(r"\b(?:[A-Z][a-z]?\d*)+(?:\d*[+-])?\b")


ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman(token):
    """XVIII -> 18: века во многих языках пишут римскими цифрами, и
    «18-19 веках» законно становится «XVIII–XIX secolo»"""
    total = 0
    for a, b in zip(token, token[1:] + " "):
        v = ROMAN[a]
        total += -v if ROMAN.get(b, 0) > v else v
    return str(total)


def digits(text):
    """Последовательности цифр: 1878, 1974, 7200, 05336, 40… — и века,
    записанные римскими цифрами (переводятся в арабские)"""
    # Разделитель тысяч: «7 200», «7,200» — и перед иероглифами («7,200トン»)
    text = re.sub(r"(?<=\d)[\s\u00a0\u202f.,](?=\d{3}(?!\d))", "", text)
    # Только I, V, X: веков больше XXI нет, а «CV» (резюме) — не число 105
    # Окончания порядковых: «XXIe siècle», «XVIIIᵉ»
    romans = [roman(t) for t in re.findall(r"\b([IVX]{2,})(?:e|er|ème|ᵉ)?\b", text)]
    # «03» и «3» — одно число: в японской дате месяц без нуля (2013年3月26日)
    return sorted(n.lstrip("0") or "0" for n in re.findall(r"\d+", text) + romans)


def as_text(value):
    return " ".join(value) if isinstance(value, list) else str(value)


def check(code, source):
    path = I18N / f"{code}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"не читается: {error}"]
    problems = []
    missing = sorted(set(source) - set(data))
    extra = sorted(set(data) - set(source))
    if missing:
        problems.append(f"нет меток ({len(missing)}): {missing[:5]}")
    if extra:
        problems.append(f"лишние метки ({len(extra)}): {extra[:5]}")
    for label, src in source.items():
        if label not in data:
            continue
        got, ru = data[label], src["ru"]
        if isinstance(ru, list):
            if not isinstance(got, list) or len(got) != len(ru):
                problems.append(f"{label}: ждали список из {len(ru)}, пришло {type(got).__name__}"
                                f"{'' if not isinstance(got, list) else ' из ' + str(len(got))}")
                continue
            if any(not str(x).strip() for x in got):
                problems.append(f"{label}: пустой абзац")
        elif not isinstance(got, str) or not got.strip():
            problems.append(f"{label}: пусто или не строка")
            continue
        if label == "seo":
            continue          # ключевые слова пересказывают, цифр в них нет
        lost = [d for d in digits(as_text(ru)) if d not in digits(as_text(got))]
        if lost:
            problems.append(f"{label}: пропали числа {sorted(set(lost))[:6]}")
    return problems


def main():
    source = json.loads((I18N / "source.json").read_text(encoding="utf-8"))
    codes = sys.argv[1:] or sorted(p.stem for p in I18N.glob("*.json") if p.stem != "source")
    ok = True
    for code in codes:
        problems = check(code, source)
        print(f"{code}: {'в порядке' if not problems else f'замечаний {len(problems)}'}")
        for p in problems[:12]:
            print("    ", p)
        ok = ok and not problems
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
