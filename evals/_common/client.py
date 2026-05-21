"""Shared OpenAI-compatible client for the LumynaX gateway, used by every runner."""
import os, time, json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import httpx


@dataclass
class GatewayClient:
    base_url: str = "http://localhost:8080/v1"
    api_key:  str = "lumynax-local-dev"
    timeout:  float = 300.0

    def chat(self, model: str, messages: list[dict],
             temperature: float = 0.2, max_tokens: int = 512,
             response_format: Optional[dict] = None) -> str:
        body = {"model": model, "messages": messages,
                "temperature": temperature, "max_tokens": max_tokens}
        if response_format: body["response_format"] = response_format
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(f"{self.base_url}/chat/completions", json=body,
                        headers={"Authorization": f"Bearer {self.api_key}"})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    def embed(self, model: str, inputs: list[str]) -> list[list[float]]:
        with httpx.Client(timeout=self.timeout) as c:
            r = c.post(f"{self.base_url}/embeddings",
                        json={"model": model, "input": inputs},
                        headers={"Authorization": f"Bearer {self.api_key}"})
            r.raise_for_status()
            return [d["embedding"] for d in r.json()["data"]]


def save_result(model: str, benchmark: str, score: float, details: dict, evals_dir: Path) -> Path:
    """Write a uniform result JSON under evals/<benchmark>/results/<model>.json."""
    out = evals_dir / benchmark / "results" / f"{model}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": model, "benchmark": benchmark, "score": score,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "details": details,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out
