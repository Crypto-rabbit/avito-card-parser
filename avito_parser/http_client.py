from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener, urlopen


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)


@dataclass
class HttpResponse:
    url: str
    status_code: int
    text: str
    error: str = ""


@dataclass
class ProxyConfig:
    http_proxy: str = ""
    https_proxy: str = ""
    rotate_url: str = ""
    cards_per_ip: int = 95
    rotate_sleep: float = 8.0


class HttpClient:
    def __init__(self, timeout: float = 30.0, user_agent: str = DEFAULT_UA, proxy: ProxyConfig | None = None):
        self.timeout = timeout
        self.user_agent = user_agent
        self.proxy = proxy or ProxyConfig()
        self.cards_on_ip = 0
        self.opener = self._build_opener()

    def get(self, url: str) -> HttpResponse:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
                "Connection": "close",
            },
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                text = response.read().decode("utf-8", errors="replace")
                return HttpResponse(url, response.status, text)
        except HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return HttpResponse(url, exc.code, text, f"http_{exc.code}")
        except (TimeoutError, URLError, OSError) as exc:
            return HttpResponse(url, 0, "", str(exc))

    def count_card(self) -> None:
        self.cards_on_ip += 1

    def should_rotate(self) -> bool:
        return bool(self.proxy.rotate_url and self.cards_on_ip >= self.proxy.cards_per_ip)

    def rotate_ip(self) -> bool:
        if not self.proxy.rotate_url:
            return False
        try:
            urlopen(self.proxy.rotate_url, timeout=self.timeout).read()
            time.sleep(self.proxy.rotate_sleep)
            self.cards_on_ip = 0
            self.opener = self._build_opener()
            return True
        except OSError:
            return False

    def _build_opener(self):
        proxies = {}
        if self.proxy.http_proxy:
            proxies["http"] = self.proxy.http_proxy
        if self.proxy.https_proxy:
            proxies["https"] = self.proxy.https_proxy
        return build_opener(ProxyHandler(proxies)) if proxies else build_opener()

