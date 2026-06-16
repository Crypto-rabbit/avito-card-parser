from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.request import Request, urlopen


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect sample Avito card URLs from a public page")
    parser.add_argument("--source", default="https://www.avito.ru/", help="Avito page with item links")
    parser.add_argument("-o", "--output", default="examples/urls.txt")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    request = Request(args.source, headers={"User-Agent": UA, "Accept-Language": "ru-RU,ru;q=0.9"})
    with urlopen(request, timeout=30) as response:
        content = response.read().decode("utf-8", errors="replace")

    paths = []
    for match in re.finditer(r'"urlPath":"(?P<url>/[^"\\]+_\d+[^"\\]*)"', content):
        path = match.group("url").replace("\\u0026", "&")
        path = re.sub(r"\?.*$", "", path)
        if path not in paths:
            paths.append(path)

    urls = ["https://www.avito.ru" + path for path in paths[: args.limit]]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(urls) + "\n", encoding="utf-8")
    print(f"Saved {len(urls)} URLs to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

