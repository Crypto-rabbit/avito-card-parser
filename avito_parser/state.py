from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CrawlState:
    seen_urls: set[str] = field(default_factory=set)
    done_item_ids: set[str] = field(default_factory=set)
    queue: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "CrawlState":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            seen_urls=set(data.get("seen_urls", [])),
            done_item_ids=set(data.get("done_item_ids", [])),
            queue=list(data.get("queue", [])),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "seen_urls": sorted(self.seen_urls),
            "done_item_ids": sorted(self.done_item_ids),
            "queue": self.queue,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

