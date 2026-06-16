# Avito Card Parser

Lightweight CLI parser for public Avito item cards.

The main optimization is simple: collect card data from the HTML response and embedded page data instead of opening every card in a full browser. This avoids loading images, fonts, analytics, and client scripts for every item.

## What It Extracts

- URL
- item ID
- title
- price
- seller
- location
- description
- images count
- status/error

## Why This Is Faster

A browser-based scraper can load megabytes of extra static assets per card. This parser requests only the card HTML and parses the fields locally.

In a short local benchmark on 8 public cards, all 8 returned `ok`; the measured technical speed with a 1-2 second delay was about `850 cards/hour`. For production-like use on one IP, the safer target is much lower: `90-100 cards/hour`.

For a target of 90-100 cards/hour on one IP, use a delay around 36-42 seconds:

```powershell
python run_parser.py -i examples/urls.txt -o out/cards.csv --min-delay 36 --max-delay 42 --resume
```

For a short technical benchmark, use a smaller delay:

```powershell
python run_parser.py -i examples/urls.txt -o out/test.csv --min-delay 1 --max-delay 2
```

## Notes

This project does not bypass captcha, access restrictions, authentication, or paywalls. If Avito returns a restriction page, the parser records the status and slows down on the next request.

Run checks:

```powershell
python -m compileall .
python -m unittest discover -s tests
```

## Portfolio Summary

Built a lightweight Avito card parser that extracts product data from HTML without full browser rendering. Added adaptive delays, progress saving, CSV/JSON export, and speed measurement for stable long-running collection.
