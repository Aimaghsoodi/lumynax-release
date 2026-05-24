"""User config — ~/.lumynax/config.toml — gateway URL, default model, default strategy."""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional


def home() -> Path:
    return Path(os.environ.get("LUMYNAX_HOME", Path.home() / ".lumynax"))


def config_path() -> Path:
    return home() / "config.toml"


@dataclass
class Config:
    gateway_url:      str = os.environ.get("LUMYNAX_GATEWAY", "http://localhost:8080")
    api_key:          str = os.environ.get("LUMYNAX_KEY", "lumynax-local-dev")
    default_model:    Optional[str] = None
    default_strategy: str = "balanced"
    default_jurisdiction: str = "NZ"
    streaming:        bool = True
    color:            bool = True
    pull_concurrency: int = 4


def load() -> Config:
    p = config_path()
    if not p.exists(): return Config()
    try:
        import tomllib
        with p.open("rb") as f:
            data = tomllib.load(f)
        c = Config()
        for k, v in (data.get("lumynax") or {}).items():
            if hasattr(c, k): setattr(c, k, v)
        return c
    except Exception:
        return Config()


def save(c: Config) -> None:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[lumynax]"]
    for k, v in asdict(c).items():
        if isinstance(v, str):
            lines.append(f'{k} = "{v}"')
        elif isinstance(v, bool):
            lines.append(f"{k} = {'true' if v else 'false'}")
        elif v is None:
            continue
        else:
            lines.append(f"{k} = {v}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
