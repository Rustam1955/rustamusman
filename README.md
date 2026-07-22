# Персональный научный сайт — Усманов Рустамжон

Двуязычный (RU/EN) сайт-визитка учёного на Flask. Публикации подтягиваются
с профиля [ИСТИНА МГУ](https://istina.msu.ru/workers/258800219/).

## Стек
- **Python 3 + Flask** — бэкенд и рендеринг страниц (Jinja2)
- **requests + BeautifulSoup** — парсер публикаций с ИСТИНА
- **Ванильный CSS/JS** — современный минимализм, светлая/тёмная тема, адаптив

## Запуск локально
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
# открыть http://127.0.0.1:5000
```

## Обновить список публикаций с ИСТИНА
```bash
.venv/bin/python scraper/scrape_istina.py
```
Данные сохраняются в `data/publications.json`.

## Структура
```
app.py                     Flask-приложение и маршруты (RU/EN)
data/profile.json          Биография, CV, ссылки, email
data/publications.json     Публикации (генерируется парсером)
scraper/scrape_istina.py   Парсер профиля ИСТИНА
templates/                 HTML-шаблоны (Jinja2)
static/css/style.css       Стили
static/js/filter.js        Фильтр публикаций
static/img/                Фото (положите photo.jpg)
static/pdfs/               PDF-файлы работ
```

## Как добавить свои данные
- **Фото:** положите файл в `static/img/photo.jpg`.
- **Биография / CV / email:** отредактируйте `data/profile.json`.
- **PDF публикации:** положите файл в `static/pdfs/`, затем в `data/publications.json`
  у нужной работы добавьте поле `"pdf": "имя-файла.pdf"` — появится кнопка «Скачать PDF».
- **Патенты и др.:** можно дописать вручную в `data/publications.json`
  (поля: `year, title, url, authors, type, type_ru, type_en`).

## Развёртывание
Flask требует постоянно работающий сервер (Render, Railway, PythonAnywhere, VPS).
Для бесплатного статического хостинга (GitHub Pages) сайт можно позже
преобразовать в статику через Frozen-Flask.
