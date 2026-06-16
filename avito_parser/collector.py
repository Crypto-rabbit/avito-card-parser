from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from .parser import normalize_url


def extract_card_urls(page_url: str, content: str) -> list[str]:
    urls: list[str] = []
    patterns = [
        r'"urlPath"\s*:\s*"(?P<url>/[^"\\]+_\d+[^"\\]*)"',
        r'href="(?P<url>/[^"]+_\d+(?:\?[^"]*)?)"',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            raw = match.group("url").replace("\\u0026", "&")
            raw = re.sub(r"\?.*$", "", raw)
            absolute = normalize_url(urljoin(page_url, raw))
            if "avito.ru" in absolute and absolute not in urls:
                urls.append(absolute)
    return urls


def with_page(url: str, page: int) -> str:
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if page <= 1:
        query.pop("p", None)
    else:
        query["p"] = str(page)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))

