"""Regenerate evals/results.md from per-model JSON results."""
import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
UPSTREAM = {
    "humaneval": {
        "lumynax-coder-deepseek-v2-lite-16b-gguf": 81.1,
        "lumynax-frontier-coder-qwen3-480b-a35b-gguf": 89.0,
        "lumynax-frontier-coder-deepseek-v25-1210-gguf": 89.0,
        "lumynax-coder-codellama-70b-instruct-gguf": 67.8,
        "lumynax-coder-qwen25-coder-32b-gguf": 92.7,
        "lumynax-coder-starcoder2-15b-gguf": 57.3,
        "lumynax-coder-yi-coder-9b-gguf": 57.3,
    },
    "mmlu": {
        "lumynax-frontier-qwen25-72b-instruct-gguf": 86.1,
        "lumynax-frontier-olmo2-32b-instruct": 79.8,
        "lumynax-chat-yi-15-34b-gguf": 77.1,
        "lumynax-frontier-phi-4-14b-gguf": 84.8,
        "lumynax-chat-hermes-3-llama31-8b-gguf": 68.0,
    },
}


def load_result(bench, model) -> float | None:
    p = EVAL_DIR / bench / "results" / f"{model}.json"
    if not p.exists(): return None
    return json.loads(p.read_text(encoding="utf-8")).get("score")


def main():
    lines = ["# LumynaX benchmark results\n",
             "Auto-generated. Upstream numbers cited. LumynaX numbers from `evals/<bench>/results/*.json`.\n"]
    for bench, models in UPSTREAM.items():
        lines.append(f"## {bench.upper()}\n")
        lines.append("| Model | LumynaX | Upstream | Δ |")
        lines.append("| --- | --- | --- | --- |")
        for m, up in models.items():
            lx = load_result(bench, m)
            lx_s = f"{lx*100:.1f}" if lx is not None else "_pending_"
            delta = f"{(lx*100 - up):+.1f}" if lx is not None else "—"
            lines.append(f"| `{m}` | {lx_s} | **{up}** | {delta} |")
        lines.append("")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
