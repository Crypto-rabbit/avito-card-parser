# Avito Card Parser Core

Python CLI core for collecting public Avito card data from search pages, seller profiles, or a prepared list of card URLs.

The main optimization is simple: collect card data from the HTML response and embedded page data instead of opening every card in a full browser. This avoids loading images, fonts, analytics, and client scripts for every item.

## What It Does

- accepts a search/profile URL or a TXT file with card URLs;
- collects card links from result/profile pages;
- opens every card with lightweight HTTP requests, without Selenium/Playwright;
- extracts public fields and maps them to the report columns from the sample Google Sheet;
- saves progress and avoids duplicates;
- supports HTTP mobile proxy config and rotation URL;
- writes CSV immediately and can append to Google Sheets when credentials are provided.

## Why This Is Faster

A browser-based scraper can load megabytes of extra static assets per card. This parser requests only the card HTML and parses the fields locally.

In a short local benchmark on 8 public cards, all 8 returned `ok`; the measured technical speed with a 1-2 second delay was about `850 cards/hour`. For production-like use on one IP, the safer target is much lower: `90-100 cards/hour`.

## Config

Copy `config.example.json` and edit proxy / Google Sheets settings:

```powershell
copy config.example.json config.json
```

Important fields:

- `source_url`: search results or seller profile URL.
- `limit`: number of cards to collect, up to 5000.
- `cards_per_ip`: rotate after this many parsed cards, normally 90-100.
- `rotate_url`: mobile proxy IP rotation URL.
- `http_proxy` / `https_proxy`: HTTP mobile proxy.
- `google_sheets`: service account settings.

## Run

From search/profile URL:

```powershell
python run_parser.py --config config.json --source "https://www.avito.ru/krasnodar/..." --limit 100 --resume
```

From a list of card URLs:

```powershell
python run_parser.py -i examples/urls.txt -o out/avito_report.csv --limit 20 --min-delay 36 --max-delay 42 --resume
```

Short benchmark:

```powershell
python run_parser.py -i examples/urls.txt -o out/test_report.csv --limit 8 --min-delay 1 --max-delay 2
```

## Report Format

The CSV report uses the same column layout as the provided Google Sheets example:

`Позиция`, `Категория`, `Комплектующие -> Ножки`, `Заголовок`, `Пр.Всего`, `Пр.Сегод.`, `Цена`, `Описание`, `№ объяв.`, `Характеристики`, `Продавец`, `Широта`, `Долгота`, `Город`, `Ссылка`, `Фото шт.`, `фото1`, `фото2`, `фото3`, and other characteristic columns.

## Notes

This project does not bypass captcha, access restrictions, authentication, or paywalls. If Avito returns a restriction page, the parser records the status, rotates IP when configured, and continues from the same queue.

Run checks:

```powershell
python -m compileall .
python -m unittest discover -s tests
```

## Portfolio Summary

Built a lightweight Avito card parser that extracts product data from HTML without full browser rendering. Added adaptive delays, progress saving, CSV/JSON export, and speed measurement for stable long-running collection.
