from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def default_ledger_path() -> Path:
    return Path.cwd() / ".sovereigncode" / "audit.jsonl"


@dataclass(slots=True)
class AuditLedger:
    path: Path
    _lock: threading.Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def append(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            sequence = self._line_count() + 1
            record = {
                "ledger_sequence": sequence,
                "ledger_timestamp": datetime.now(UTC).isoformat(),
                "event": event,
                "payload": payload,
            }
            record["ledger_id"] = self._digest(record)
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
                stream.write("\n")
            return {**record, "ledger_path": str(self.path)}

    def tail(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8-sig").splitlines()
        records: list[dict[str, Any]] = []
        for line in lines[-max(1, limit) :]:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                payload["ledger_path"] = str(self.path)
                records.append(payload)
        return records

    def _line_count(self) -> int:
        if not self.path.exists():
            return 0
        with self.path.open("r", encoding="utf-8-sig") as stream:
            return sum(1 for line in stream if line.strip())

    @staticmethod
    def _digest(record: dict[str, Any]) -> str:
        raw = json.dumps(record, sort_keys=True, default=str).encode("utf-8")
        return f"sc-ledger-{hashlib.sha256(raw).hexdigest()[:24]}"
