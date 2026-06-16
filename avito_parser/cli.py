from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .parser import AvitoCard, detect_block, normalize_url, parse_card


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    urls = load_urls(args.input)
    if not urls:
        print("No URLs found.", file=sys.stderr)
        return 2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    progress_path = output.with_suffix(output.suffix + ".progress.json")
    done = load_progress(progress_path) if args.resume else set()
    rows: list[AvitoCard] = []
    started = time.perf_counter()

    for index, url in enumerate(urls, start=1):
        normalized = normalize_url(url)
        if normalized in done:
            continue

        request_started = time.perf_counter()
        card = fetch_and_parse(normalized, args.timeout, args.user_agent)
        elapsed = time.perf_counter() - request_started
        rows.append(card)
        done.add(normalized)
        save_progress(progress_path, done)

        safe_title = safe_console(card.title[:80] or normalized)
        print(f"{index}/{len(urls)} {card.status:<12} {elapsed:>5.2f}s {safe_title}")

        if index < len(urls):
            delay = adaptive_delay(args.min_delay, args.max_delay, card.status)
            time.sleep(delay)

    write_output(output, rows, args.format)
    total = max(time.perf_counter() - started, 0.001)
    speed = len(rows) / total * 3600
    print(f"Saved {len(rows)} rows to {output}")
    print(f"Measured speed: {speed:.1f} cards/hour for this run")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lightweight Avito card parser")
    parser.add_argument("-i", "--input", required=True, help="TXT file with one Avito URL per line")
    parser.add_argument("-o", "--output", default="out/avito_cards.csv", help="Output CSV/JSON path")
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--min-delay", type=float, default=36.0, help="Minimum delay between cards")
    parser.add_argument("--max-delay", type=float, default=42.0, help="Maximum delay between cards")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--resume", action="store_true", help="Skip URLs saved in progress file")
    parser.add_argument("--user-agent", default=DEFAULT_UA)
    return parser


def load_urls(path: str) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def fetch_and_parse(url: str, timeout: float, user_agent: str) -> AvitoCard:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Connection": "close",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status_code = response.status
            content = response.read().decode("utf-8", errors="replace")
        blocked = detect_block(content, status_code)
        if blocked:
            return parse_card(url, content, status=f"blocked:{blocked}", error=blocked)
        return parse_card(url, content, status="ok")
    except HTTPError as exc:
        content = exc.read().decode("utf-8", errors="replace")
        blocked = detect_block(content, exc.code) or f"http_{exc.code}"
        return parse_card(url, content, status=f"error:{exc.code}", error=blocked)
    except (TimeoutError, URLError, OSError) as exc:
        return AvitoCard(url, "", "", "", "", "", "", "", "error", str(exc))


def adaptive_delay(min_delay: float, max_delay: float, status: str) -> float:
    delay = random.uniform(min_delay, max_delay)
    if status.startswith("blocked") or status.startswith("error:429") or status.startswith("error:403"):
        delay = max(delay * 3, 120.0)
    return delay


def write_output(path: Path, rows: list[AvitoCard], fmt: str) -> None:
    if fmt == "json":
        path.write_text(
            json.dumps([row.to_dict() for row in rows], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return

    fields = list(AvitoCard.__dataclass_fields__.keys())
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())


def load_progress(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(json.loads(path.read_text(encoding="utf-8")))


def save_progress(path: Path, urls: set[str]) -> None:
    path.write_text(json.dumps(sorted(urls), ensure_ascii=False, indent=2), encoding="utf-8")


def safe_console(value: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return value.encode(encoding, errors="replace").decode(encoding, errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
