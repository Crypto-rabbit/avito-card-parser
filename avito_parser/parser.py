from __future__ import annotations

import html
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlsplit, urlunsplit


@dataclass
class AvitoCard:
    url: str
    item_id: str
    title: str
    category: str
    breadcrumbs: str
    price: str
    total_views: str
    today_views: str
    promotion: str
    boost_time: str
    seller: str
    location: str
    latitude: str
    longitude: str
    description: str
    description_chars: str
    delivery: str
    can_call: str
    can_message: str
    verified_requisites: str
    characteristics_text: str
    images_count: str
    photo1: str
    photo2: str
    photo3: str
    status: str
    error: str = ""
    characteristics: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    if not parts.scheme:
        url = "https://" + url.strip().lstrip("/")
        parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def parse_card(url: str, content: str, status: str = "ok", error: str = "") -> AvitoCard:
    clean = _clean_html(content)
    text = _script_text(content)
    embedded = _extract_embedded_json(content)
    item_id = _first_match(url, r"_(\d{6,})(?:\?|$)") or _json_find(embedded, "id")
    description = _extract_description(content)
    photos = _extract_photo_urls(content)
    characteristics = _extract_characteristics(text + "\n" + clean)
    latitude, longitude = _extract_coords(content)

    return AvitoCard(
        url=url,
        item_id=item_id,
        title=_extract_title(content, embedded),
        category=_extract_category(url, text, embedded),
        breadcrumbs=_extract_breadcrumbs(text),
        price=_extract_price(content, clean, embedded),
        total_views=_extract_views(text, "total"),
        today_views=_extract_views(text, "today"),
        promotion=_extract_yes_no(text, ["x-promoted", "promotion", "Продвиж"]),
        boost_time=_first_match(text, r"(?:Время поднятия|Поднято)\s*:?\s*([0-9:. -]+)"),
        seller=_extract_seller(content, clean, embedded),
        location=_extract_location(content, embedded),
        latitude=latitude,
        longitude=longitude,
        description=description,
        description_chars=str(len(description)),
        delivery=_extract_yes_no(text, ["delivery", "Доставка", "Авито Доставка"]),
        can_call=_extract_yes_no(text, ["phone", "Позвонить"]),
        can_message=_extract_yes_no(text, ["messenger", "Написать"]),
        verified_requisites=_extract_yes_no(text, ["Реквизиты проверены", "verified"]),
        characteristics_text=_format_characteristics(characteristics),
        images_count=_extract_images_count(content, embedded, photos),
        photo1=photos[0] if len(photos) > 0 else "",
        photo2=photos[1] if len(photos) > 1 else "",
        photo3=photos[2] if len(photos) > 2 else "",
        status=status,
        error=error,
        characteristics=characteristics,
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


def _extract_category(url: str, text: str, embedded: Any) -> str:
    category = _first_match(text, r'\\"categorySlug\\"\s*:\s*\\"([^"\\]+)\\"')
    if category:
        return category.replace("_", " ")
    path_parts = [part for part in urlsplit(url).path.split("/") if part]
    if len(path_parts) >= 2:
        return path_parts[1].replace("_", " ")
    return str(_json_find(embedded, "categorySlug") or "")


def _extract_breadcrumbs(text: str) -> str:
    names = []
    category_block = _first_match(text, r'\\"categoryTree\\"\s*:\s*(\[.*?\])\s*,\\"')
    source = category_block or text
    for name in re.findall(r'\\"name\\"\s*:\s*\\"([^"\\]+)\\"', source):
        if name not in names and name not in {"Все категории"}:
            names.append(name)
        if len(names) >= 4:
            break
    return " -> ".join(names)


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


def _extract_coords(content: str) -> tuple[str, str]:
    lat = _first_match(content, r'\\"latitude\\"\s*:\s*([0-9.-]+)')
    lon = _first_match(content, r'\\"longitude\\"\s*:\s*([0-9.-]+)')
    if lat and lon:
        return lat.replace(".", ","), lon.replace(".", ",")
    coords = re.search(r'\\"geoCoords\\"\s*:\s*\[\s*([0-9.-]+)\s*,\s*([0-9.-]+)\s*\]', content)
    if coords:
        return coords.group(1).replace(".", ","), coords.group(2).replace(".", ",")
    return "", ""


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


def _extract_images_count(content: str, embedded: Any, photos: list[str] | None = None) -> str:
    value = _json_find(embedded, "imagesCount")
    if value not in {None, ""}:
        return str(value)
    if photos:
        return str(len(photos))
    urls = set(re.findall(r"https://[^\"']+img\.avito\.st/[^\"']+", content))
    return str(len(urls)) if urls else ""


def _extract_photo_urls(content: str) -> list[str]:
    urls = []
    for url in re.findall(r"https://[^\"'\\]+img\.avito\.st/[^\"'\\]+", content):
        url = url.replace("\\u0026", "&")
        if url not in urls:
            urls.append(url)
        if len(urls) >= 20:
            break
    return urls


KNOWN_CHARACTERISTICS = [
    "Состояние",
    "Доступность",
    "Ширина",
    "Высота",
    "Длина",
    "Длина в разложенном виде",
    "Длина в сложенном виде",
    "Количество кресел",
    "Количество стульев",
    "Материал основания",
    "Материал столешницы",
    "Основной цвет",
    "Основной цвет столешницы",
    "Раскладной механизм",
    "Раскладной механизм у стола",
    "Состав комплекта",
    "Тип стола",
    "Тип товара",
    "Форма",
    "Форма стола",
    "Что есть у товара",
]


def _extract_characteristics(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    normalized = _space(text.replace("\\n", "\n"))
    keys = "|".join(re.escape(key) for key in KNOWN_CHARACTERISTICS)
    for key in KNOWN_CHARACTERISTICS:
        patterns = [
            rf'{re.escape(key)}\s*:\s*([^:]+?)(?=\s+(?:{keys})\s*:|$)',
            rf'\\"title\\"\s*:\s*\\"{re.escape(key)}\\"\s*,.*?\\"(?:value|text|title)\\"\s*:\s*\\"([^"\\]+)\\"',
        ]
        for pattern in patterns:
            value = _first_match(normalized, pattern)
            value = _space(value)
            if value:
                result[key] = value[:160]
                break
    return result


def _format_characteristics(characteristics: dict[str, str]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in characteristics.items())


def _extract_views(text: str, kind: str) -> str:
    if kind == "today":
        patterns = [
            r"(?:просмотр(?:ов|а)?\s+сегодня|сегодня\s+просмотр(?:ов|а)?)[^0-9]{0,30}([0-9 ]{1,8})",
            r'\\"todayViews\\"\s*:\s*([0-9]+)',
        ]
    else:
        patterns = [
            r"(?:всего\s+просмотр(?:ов|а)?|просмотр(?:ов|а)?\s+всего)[^0-9]{0,30}([0-9 ]{1,8})",
            r'\\"totalViews\\"\s*:\s*([0-9]+)',
        ]
    for pattern in patterns:
        value = _first_match(text, pattern)
        if value:
            return _space(value)
    return ""


def _extract_yes_no(text: str, needles: list[str]) -> str:
    lowered = text.lower()
    return "Да" if any(needle.lower() in lowered for needle in needles) else ""


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


def _script_text(content: str) -> str:
    value = html.unescape(content)
    value = value.replace('\\"', '"').replace("\\/", "/")
    value = re.sub(r"<[^>]+>", " ", value)
    return _space(value)


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
