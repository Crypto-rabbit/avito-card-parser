from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

from .collector import extract_card_urls, with_page
from .http_client import DEFAULT_UA, HttpClient, ProxyConfig
from .parser import AvitoCard, detect_block, normalize_url, parse_card
from .report import write_raw_json, write_report_csv
from .sheets import append_to_google_sheet
from .state import CrawlState


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)

    source = args.source or config.get("source_url")
    if not source and not args.input:
        print("Use --source for search/profile URL or --input for card URLs.", file=sys.stderr)
        return 2

    output = Path(args.output or config.get("output_csv", "out/avito_report.csv"))
    state_path = Path(args.state or config.get("state_file", "out/state.json"))
    raw_json = Path(args.raw_json or config.get("raw_json", "out/raw_cards.json"))
    limit = int(args.limit or config.get("limit", 100))
    min_delay = float(args.min_delay if args.min_delay is not None else config.get("min_delay", 36.0))
    max_delay = float(args.max_delay if args.max_delay is not None else config.get("max_delay", 42.0))
    page_delay = float(config.get("page_delay", 1.0))

    proxy_cfg = ProxyConfig(
        http_proxy=os.getenv("AVITO_HTTP_PROXY", config.get("http_proxy", "")),
        https_proxy=os.getenv("AVITO_HTTPS_PROXY", config.get("https_proxy", config.get("http_proxy", ""))),
        rotate_url=os.getenv("AVITO_ROTATE_URL", config.get("rotate_url", "")),
        cards_per_ip=int(os.getenv("AVITO_CARDS_PER_IP", config.get("cards_per_ip", 95))),
        rotate_sleep=float(os.getenv("AVITO_ROTATE_SLEEP", config.get("rotate_sleep", 8.0))),
    )
    client = HttpClient(
        timeout=float(config.get("timeout", 30.0)),
        user_agent=config.get("user_agent", DEFAULT_UA),
        proxy=proxy_cfg,
    )
    state = CrawlState.load(state_path) if args.resume else CrawlState()

    if args.input:
        for url in load_urls(args.input):
            enqueue(state, normalize_url(url))
    else:
        collect_from_source(client, state, normalize_url(source), limit, page_delay)

    cards: list[AvitoCard] = []
    started = time.perf_counter()

    while state.queue and len(cards) < limit:
        url = state.queue.pop(0)
        if url in state.seen_urls:
            continue

        request_started = time.perf_counter()
        response = client.get(url)
        elapsed = time.perf_counter() - request_started
        blocked = detect_block(response.text, response.status_code) if response.text else response.error

        if blocked:
            card = parse_card(url, response.text, status=f"blocked:{blocked}", error=blocked)
            print_line(len(cards) + 1, limit, card, elapsed)
            client.rotate_ip()
            enqueue(state, url)
            state.save(state_path)
            continue

        card = parse_card(url, response.text, status="ok")
        if card.item_id and card.item_id in state.done_item_ids:
            continue
        cards.append(card)
        state.seen_urls.add(url)
        if card.item_id:
            state.done_item_ids.add(card.item_id)
        client.count_card()
        state.save(state_path)
        print_line(len(cards), limit, card, elapsed)

        if client.should_rotate():
            client.rotate_ip()
        if state.queue and len(cards) < limit:
            time.sleep(random.uniform(min_delay, max_delay))

    write_report_csv(output, cards)
    write_raw_json(raw_json, cards)

    sheets = config.get("google_sheets", {})
    if sheets.get("enabled"):
        append_to_google_sheet(
            cards,
            credentials_path=sheets["credentials_path"],
            spreadsheet_id=sheets["spreadsheet_id"],
            worksheet_range=sheets.get("range", "A1"),
        )

    total = max(time.perf_counter() - started, 0.001)
    print(f"Saved report: {output}")
    print(f"Saved raw JSON: {raw_json}")
    print(f"Collected: {len(cards)}")
    print(f"Measured speed: {len(cards) / total * 3600:.1f} cards/hour")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Avito search/profile/card parser core")
    parser.add_argument("--source", help="Search results URL or seller profile URL")
    parser.add_argument("-i", "--input", help="TXT file with one Avito card URL per line")
    parser.add_argument("-n", "--limit", type=int, help="Cards to collect, up to 5000")
    parser.add_argument("-o", "--output", help="Report CSV path")
    parser.add_argument("--raw-json", help="Raw JSON output path")
    parser.add_argument("--config", default="config.example.json")
    parser.add_argument("--state", help="State/progress JSON path")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--min-delay", type=float)
    parser.add_argument("--max-delay", type=float)
    return parser


def load_config(path: str) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def load_urls(path: str) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def collect_from_source(client: HttpClient, state: CrawlState, source_url: str, limit: int, page_delay: float) -> None:
    page = 1
    empty_pages = 0
    source_block_retries = 0
    while len(state.queue) < limit and empty_pages < 2:
        page_url = with_page(source_url, page)
        response = client.get(page_url)
        blocked = detect_block(response.text, response.status_code) if response.text else response.error
        if blocked:
            print(f"source blocked: {blocked}; rotating IP if configured")
            if client.rotate_ip() and source_block_retries < 5:
                source_block_retries += 1
                continue
            break
        if response.status_code != 200:
            break
        urls = extract_card_urls(page_url, response.text)
        added = 0
        for url in urls:
            if enqueue(state, url):
                added += 1
            if len(state.queue) >= limit:
                break
        empty_pages = empty_pages + 1 if added == 0 else 0
        page += 1
        time.sleep(page_delay)


def enqueue(state: CrawlState, url: str) -> bool:
    if url in state.seen_urls or url in state.queue:
        return False
    state.queue.append(url)
    return True


def print_line(index: int, total: int, card: AvitoCard, elapsed: float) -> None:
    safe_title = safe_console(card.title[:80] or card.url)
    print(f"{index}/{total} {card.status:<18} {elapsed:>5.2f}s {safe_title}")


def safe_console(value: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return value.encode(encoding, errors="replace").decode(encoding, errors="replace")


if __name__ == "__main__":
    raise SystemExit(main())
