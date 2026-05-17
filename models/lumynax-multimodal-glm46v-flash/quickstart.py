from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

MODEL_TITLE = "LumynaX Multimodal GLM 4.6V Flash"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Run a local multimodal GGUF prompt for {MODEL_TITLE}.")
    parser.add_argument("--prompt", default="Describe this image in one concise paragraph.")
    parser.add_argument("--image", default="", help="Optional local image path for multimodal vision inference.")
    parser.add_argument("--system-prompt", default="", help="Optional system prompt override.")
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--ctx-size", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--threads", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--llama-cli", default="", help="Optional explicit path to llama-cli.")
    return parser


def _preferred_gguf(root: Path) -> Path:
    gguf_candidates = [
        path
        for path in sorted(root.glob("*.gguf"))
        if "mmproj" not in path.name.lower()
    ]
    if not gguf_candidates:
        raise SystemExit(f"No model GGUF file was found in {root}")
    for path in gguf_candidates:
        if "-q" in path.stem.lower():
            return path
    return gguf_candidates[0]


def _preferred_mmproj(root: Path) -> Path:
    mmproj_candidates = [
        path
        for path in sorted(root.glob("*.gguf"))
        if "mmproj" in path.name.lower()
    ]
    if not mmproj_candidates:
        raise SystemExit(f"No multimodal projector GGUF file was found in {root}")
    for path in mmproj_candidates:
        if "q8" in path.stem.lower():
            return path
    return mmproj_candidates[0]


def _discover_llama_cli(explicit_path: str) -> Path | None:
    candidates: list[Path] = []
    if explicit_path.strip():
        candidates.append(Path(explicit_path.strip()))
    for env_var in ("LLAMA_CPP_CLI", "LLAMA_CLI_PATH"):
        raw_value = os.environ.get(env_var, "").strip()
        if raw_value:
            candidates.append(Path(raw_value))
    for binary_name in ("llama-cli", "llama-cli.exe"):
        resolved = shutil.which(binary_name)
        if resolved:
            candidates.append(Path(resolved))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> None:
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    model_path = _preferred_gguf(root)
    mmproj_path = _preferred_mmproj(root)
    llama_cli_path = _discover_llama_cli(args.llama_cli)
    if llama_cli_path is None:
        raise SystemExit(
            "A llama-cli binary is required for this multimodal GGUF package. "
            "Pass --llama-cli or set LLAMA_CPP_CLI/LLAMA_CLI_PATH.",
        )
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    system_prompt = args.system_prompt.strip() or (
        f"You are LumynaX operating from the {MODEL_TITLE} package identity. "
        "Be helpful, clear, and honest about provenance."
    )
    command = [
        str(llama_cli_path),
        "-m",
        str(model_path),
        "-mm",
        str(mmproj_path),
        "-sys",
        system_prompt,
        "-p",
        args.prompt.strip() or "Describe this image in one concise paragraph.",
        "-n",
        str(args.max_new_tokens),
        "-c",
        str(args.ctx_size),
        "--temp",
        str(args.temperature),
        "--threads",
        str(args.threads),
        "--no-display-prompt",
    ]
    if args.image.strip():
        command.extend(["--image", args.image.strip()])
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "llama-cli failed"
        raise SystemExit(detail)
    stdout = completed.stdout.strip()
    if stdout:
        print(stdout)


if __name__ == "__main__":
    main()
