from __future__ import annotations

import html
import json
import re
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit


@dataclass
class AvitoCard:
    url: str
    item_id: str
    title: str
    price: str
    seller: str
    location: str
    description: str
    images_count: str
    status: str
    error: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if not parts.scheme:
        url = "https://" + url.strip().lstrip("/")
        parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def parse_card(url: str, content: str, status: str = "ok", error: str = "") -> AvitoCard:
    clean = _clean_html(content)
    embedded = _extract_embedded_json(content)
    item_id = _first_match(url, r"_(\d{6,})(?:\?|$)") or _json_find(embedded, "id")

    return AvitoCard(
        url=url,
        item_id=item_id,
        title=_extract_title(content, embedded),
        price=_extract_price(content, clean, embedded),
        seller=_extract_seller(content, clean, embedded),
        location=_extract_location(content, embedded),
        description=_extract_description(content),
        images_count=_extract_images_count(content, embedded),
        status=status,
        error=error,
    )


def detect_block(content: str, status_code: int) -> str | None:
    if status_code in {401, 403, 429}:
        return f"http_{status_code}"
    hard_signals = [
        "Доступ ограничен",
        "Access denied",
        "Подтвердите, что вы не робот",
        "Проверка безопасности",
        "Too Many Requests",
    ]
    lowered = content.lower()
    for signal in hard_signals:
        if signal.lower() in lowered:
            return signal
    return None


def _extract_title(content: str, embedded: Any) -> str:
    h1 = _tag_text(content, "h1")
    if h1:
        return h1
    return _json_find(embedded, "title") or ""


def _extract_price(content: str, clean: str, embedded: Any) -> str:
    marker = _snippet_near(content, "item-price-value", 900)
    price = _first_match(_clean_html(marker), r"([0-9][0-9\s\u00a0]{2,}\s*₽)")
    if price:
        return _space(price)
    price = _first_match(clean, r"([0-9][0-9\s\u00a0]{2,}\s*₽)")
    if price:
        return _space(price)
    detailed = _json_find(embedded, "priceDetailed")
    if isinstance(detailed, dict):
        value = detailed.get("string") or detailed.get("value")
        return str(value or "")
    value = _json_find(embedded, "price")
    return str(value or "")


def _extract_seller(content: str, clean: str, embedded: Any) -> str:
    for pattern in [
        r'\\"seller\\"\s*:\s*{.*?\\"name\\"\s*:\s*\\"([^"\\]+)\\"',
        r'"seller"\s*:\s*{.*?"name"\s*:\s*"([^"\\]+)"',
        r'\\"person\\"\s*:\s*\\"([^"\\]+)\\"',
    ]:
        seller = _first_match(content, pattern)
        if seller:
            return _space(seller)
    marker = _snippet_near(content, 'data-marker="seller-info/name"', 800)
    seller = _clean_html(marker)
    seller = re.sub(r".*seller-info/name", "", seller, flags=re.IGNORECASE)
    seller = _space(seller)
    if seller:
        return seller[:120]
    seller_info = _json_find(embedded, "sellerInfo")
    if isinstance(seller_info, dict):
        person = seller_info.get("person") or seller_info.get("name")
        if person:
            return str(person)
    return _json_find(embedded, "sellerName") or ""


def _extract_location(content: str, embedded: Any) -> str:
    location_name = _first_match(content, r'\\"locationName\\"\s*:\s*\\"([^"\\]+)\\"')
    if location_name:
        return _space(location_name)
    alt = _first_match(content, r'"imageAlt"\s*:\s*"([^"]+)"')
    if not alt:
        alt = _first_match(content, r'\\"imageAlt\\"\s*:\s*\\"([^"\\]+)\\"')
    if alt and "," in alt:
        return _space(alt.rsplit(",", 1)[-1])
    location = _json_find(embedded, "location")
    if isinstance(location, dict):
        return str(location.get("name") or "")
    return _json_find(embedded, "locationName") or ""


def _extract_description(content: str) -> str:
    direct_match = re.search(
        r'<(?P<tag>[a-z0-9]+)[^>]*(?:class|data-marker)="[^"]*item-description[^"]*"[^>]*>(?P<v>.*?)</(?P=tag)>',
        content,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if direct_match:
        return _clean_html(direct_match.group("v"))[:2500]
    marker = _snippet_near(content, "item-description", 3000)
    text = _clean_html(marker)
    text = re.sub(r"^.*?item-description", "", text, flags=re.IGNORECASE)
    text = re.split(r"window\.|data-marker=|Пожаловаться", text, maxsplit=1)[0]
    return _space(text)[:2500]


def _extract_images_count(content: str, embedded: Any) -> str:
    value = _json_find(embedded, "imagesCount")
    if value is not None:
        return str(value)
    urls = set(re.findall(r"https://[^\"']+img\.avito\.st/[^\"']+", content))
    return str(len(urls)) if urls else ""


def _extract_embedded_json(content: str) -> Any:
    candidates = []
    for pattern in [
        r"window\.__initialData__\s*=\s*({.*?});\s*</script>",
        r"window\.__INITIAL_STATE__\s*=\s*({.*?});\s*</script>",
        r"window\.appStorage\s*=\s*({.*?});\s*</script>",
    ]:
        for match in re.finditer(pattern, content, flags=re.DOTALL):
            candidates.append(match.group(1))
    decoded = []
    for candidate in candidates[:5]:
        try:
            decoded.append(json.loads(candidate))
        except json.JSONDecodeError:
            continue
    return decoded


def _json_find(data: Any, key: str) -> Any:
    stack = [data]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if key in current:
                return current[key]
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return ""


def _tag_text(content: str, tag: str) -> str:
    value = _first_match(content, rf"<{tag}[^>]*>(.*?)</{tag}>")
    return _clean_html(value or "")


def _snippet_near(content: str, needle: str, radius: int) -> str:
    index = content.find(needle)
    if index < 0:
        return ""
    start = max(0, index - radius // 3)
    end = min(len(content), index + radius)
    return content[start:end]


def _clean_html(value: str) -> str:
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.DOTALL | re.IGNORECASE)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.DOTALL | re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    return _space(html.unescape(value))


def _first_match(value: str, pattern: str) -> str:
    match = re.search(pattern, value, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else ""


def _space(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip()
