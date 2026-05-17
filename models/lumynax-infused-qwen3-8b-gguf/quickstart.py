from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

MODEL_TITLE = "LumynaX Infused Qwen3 8B GGUF"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Run a local GGUF chat for {MODEL_TITLE}.")
    parser.add_argument(
        "--prompt",
        default=None,
        help="Prompt to send to the model.",
    )
    parser.add_argument("--system-prompt", default="", help="Optional system prompt override.")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Start an interactive terminal chat instead of running a single prompt.",
    )
    parser.add_argument("--max-new-tokens", type=int, default=192)
    parser.add_argument("--ctx-size", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--threads", type=int, default=max(1, os.cpu_count() or 1))
    parser.add_argument("--llama-cli", default="", help="Optional explicit path to llama-cli.")
    parser.add_argument(
        "--cache-local",
        action="store_true",
        help="Copy the GGUF into LOCALAPPDATA before running. Useful when a runtime cannot read network paths.",
    )
    parser.add_argument("--reasoning", choices=("on", "off", "auto"), default="off")
    parser.add_argument(
        "--reasoning-format",
        choices=("auto", "none", "deepseek", "deepseek-legacy"),
        default="auto",
    )
    parser.add_argument("--reasoning-budget", type=int, default=None)
    return parser


def _preferred_gguf(root: Path) -> Path:
    gguf_candidates = sorted(root.glob("*.gguf"))
    if not gguf_candidates:
        raise SystemExit(f"No GGUF file was found in {root}")
    for path in gguf_candidates:
        if "-q" in path.stem.lower():
            return path
    return gguf_candidates[0]


def _local_model_path(model_path: Path, *, cache_local: bool = False) -> Path:
    if not cache_local:
        return model_path
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    cache_dir = local_app_data / "tinyluminax" / "gguf-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_path = cache_dir / model_path.name
    source_stat = model_path.stat()
    if (
        not cached_path.exists()
        or cached_path.stat().st_size != source_stat.st_size
        or cached_path.stat().st_mtime_ns < source_stat.st_mtime_ns
    ):
        print(f"Caching GGUF locally at {cached_path}", file=sys.stderr)
        shutil.copy2(model_path, cached_path)
    return cached_path


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


def _extract_text(response: dict[str, object]) -> str:
    choices = response.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("The runtime returned no choices.")
    first_choice = choices[0]
    if isinstance(first_choice, dict):
        message = first_choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if content not in (None, ""):
                return str(content).strip()
        text = first_choice.get("text")
        if text not in (None, ""):
            return str(text).strip()
    raise RuntimeError("The runtime returned an unsupported response payload.")


def _run_llama_cpp_python(
    *,
    model_path: Path,
    system_prompt: str,
    user_prompt: str,
    max_new_tokens: int,
    ctx_size: int,
    temperature: float,
    threads: int,
) -> str:
    from llama_cpp import Llama

    llm = Llama(
        model_path=str(model_path),
        n_ctx=ctx_size,
        n_threads=threads,
        n_gpu_layers=0,
        chat_format="chat_template.default",
        verbose=False,
    )
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_new_tokens,
        temperature=temperature,
    )
    return _extract_text(response)


def _run_llama_cli(
    *,
    llama_cli_path: Path,
    model_path: Path,
    system_prompt: str,
    user_prompt: str,
    max_new_tokens: int,
    ctx_size: int,
    temperature: float,
    threads: int,
    reasoning: str,
    reasoning_format: str,
    reasoning_budget: int | None,
) -> None:
    command = [
        str(llama_cli_path),
        "-m",
        str(model_path),
        "-sys",
        system_prompt,
        "-p",
        user_prompt,
        "-cnv",
        "-st",
        "-n",
        str(max_new_tokens),
        "-c",
        str(ctx_size),
        "--reasoning",
        reasoning,
        "--temp",
        str(temperature),
        "--threads",
        str(threads),
        "--no-display-prompt",
    ]
    if reasoning_format != "auto":
        command.extend(["--reasoning-format", reasoning_format])
    if reasoning_budget is not None:
        command.extend(["--reasoning-budget", str(reasoning_budget)])
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


def _print_interactive_banner() -> None:
    print("LumynaX interactive terminal chat")
    print("Type /reset to clear the conversation, or /quit to exit.")


def _run_interactive_llama_cpp_python(
    *,
    model_path: Path,
    system_prompt: str,
    max_new_tokens: int,
    ctx_size: int,
    temperature: float,
    threads: int,
    opening_prompt: str | None = None,
    reasoning: str = "off",
    reasoning_format: str = "auto",
    reasoning_budget: int | None = None,
) -> None:
    from llama_cpp import Llama

    llm = Llama(
        model_path=str(model_path),
        n_ctx=ctx_size,
        n_threads=threads,
        n_gpu_layers=0,
        chat_format="chat_template.default",
        verbose=False,
    )
    transcript: list[tuple[str, str]] = []
    _print_interactive_banner()

    pending_prompt = opening_prompt.strip() if opening_prompt and opening_prompt.strip() else None
    while True:
        try:
            if pending_prompt is None:
                user_prompt = input("You> ").strip()
            else:
                user_prompt = pending_prompt
                print(f"You> {user_prompt}")
                pending_prompt = None
        except (EOFError, KeyboardInterrupt):
            print("\nExiting LumynaX chat.")
            return
        if not user_prompt:
            continue
        lowered_prompt = user_prompt.lower()
        if lowered_prompt in ('/quit', '/exit'):
            print("Exiting LumynaX chat.")
            return
        if lowered_prompt == "/reset":
            transcript.clear()
            print("Conversation reset.")
            continue
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for transcript_user_prompt, transcript_assistant_response in transcript:
            messages.append({"role": "user", "content": transcript_user_prompt})
            messages.append({"role": "assistant", "content": transcript_assistant_response})
        messages.append({"role": "user", "content": user_prompt})
        response = llm.create_chat_completion(
            messages=messages,
            max_tokens=max_new_tokens,
            temperature=temperature,
        )
        assistant_text = _extract_text(response)
        print(f"LumynaX> {assistant_text}")
        transcript.append((user_prompt, assistant_text))


def _run_interactive_llama_cli(
    *,
    llama_cli_path: Path,
    model_path: Path,
    system_prompt: str,
    max_new_tokens: int,
    ctx_size: int,
    temperature: float,
    threads: int,
    opening_prompt: str | None = None,
    reasoning: str = "off",
    reasoning_format: str = "auto",
    reasoning_budget: int | None = None,
) -> None:
    print("LumynaX interactive terminal chat")
    print("Interactive mode already uses llama-cli directly. Use Ctrl+C to exit.")
    command = [
        str(llama_cli_path),
        "-m",
        str(model_path),
        "-sys",
        system_prompt,
        "-cnv",
        "-n",
        str(max_new_tokens),
        "-c",
        str(ctx_size),
        "--reasoning",
        reasoning,
        "--temp",
        str(temperature),
        "--threads",
        str(threads),
        "--simple-io",
    ]
    if reasoning_format != "auto":
        command.extend(["--reasoning-format", reasoning_format])
    if reasoning_budget is not None:
        command.extend(["--reasoning-budget", str(reasoning_budget)])
    if opening_prompt and opening_prompt.strip():
        command.extend(["-p", opening_prompt.strip()])
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parent
    source_model_path = _preferred_gguf(root)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    single_prompt = (args.prompt or "Say hello in one short sentence.").strip()
    system_prompt = args.system_prompt.strip() or (
        f"You are LumynaX operating from the {MODEL_TITLE} package identity. "
        "Be helpful, clear, and honest about provenance."
    )
    explicit_cli_requested = bool(
        args.llama_cli.strip()
        or os.environ.get("LLAMA_CPP_CLI", "").strip()
        or os.environ.get("LLAMA_CLI_PATH", "").strip()
    )
    if args.interactive:
        llama_cli_path = _discover_llama_cli(args.llama_cli)
        if explicit_cli_requested:
            if llama_cli_path is None:
                raise SystemExit(
                    "A llama-cli override was requested, but no usable llama-cli binary was found.",
                )
            _run_interactive_llama_cli(
                llama_cli_path=llama_cli_path,
                model_path=_local_model_path(source_model_path, cache_local=args.cache_local),
                system_prompt=system_prompt,
                opening_prompt=args.prompt,
                max_new_tokens=args.max_new_tokens,
                ctx_size=args.ctx_size,
                temperature=args.temperature,
                threads=args.threads,
                reasoning=args.reasoning,
                reasoning_format=args.reasoning_format,
                reasoning_budget=args.reasoning_budget,
            )
            return
        model_path = _local_model_path(source_model_path, cache_local=args.cache_local)
        try:
            _run_interactive_llama_cpp_python(
                model_path=model_path,
                system_prompt=system_prompt,
                opening_prompt=args.prompt,
                max_new_tokens=args.max_new_tokens,
                ctx_size=args.ctx_size,
                temperature=args.temperature,
                threads=args.threads,
                reasoning=args.reasoning,
                reasoning_format=args.reasoning_format,
                reasoning_budget=args.reasoning_budget,
            )
            return
        except Exception as exc:  # noqa: BLE001
            if llama_cli_path is None:
                raise SystemExit(
                    "llama-cpp-python could not load this GGUF package. "
                    "Install or point LLAMA_CPP_CLI at llama-cli to use the built-in fallback. "
                    f"Original error: {exc}",
                ) from exc
            print(
                f"llama-cpp-python failed; falling back to llama-cli at {llama_cli_path}",
                file=sys.stderr,
            )
            _run_interactive_llama_cli(
                llama_cli_path=llama_cli_path,
                model_path=model_path,
                system_prompt=system_prompt,
                opening_prompt=args.prompt,
                max_new_tokens=args.max_new_tokens,
                ctx_size=args.ctx_size,
                temperature=args.temperature,
                threads=args.threads,
                reasoning=args.reasoning,
                reasoning_format=args.reasoning_format,
                reasoning_budget=args.reasoning_budget,
            )
            return
    if explicit_cli_requested:
        llama_cli_path = _discover_llama_cli(args.llama_cli)
        if llama_cli_path is None:
            raise SystemExit(
                "A llama-cli override was requested, but no usable llama-cli binary was found.",
            )
        _run_llama_cli(
            llama_cli_path=llama_cli_path,
            model_path=_local_model_path(source_model_path, cache_local=args.cache_local),
            system_prompt=system_prompt,
            user_prompt=single_prompt,
            max_new_tokens=args.max_new_tokens,
            ctx_size=args.ctx_size,
            temperature=args.temperature,
            threads=args.threads,
            reasoning=args.reasoning,
            reasoning_format=args.reasoning_format,
            reasoning_budget=args.reasoning_budget,
        )
        return
    model_path = _local_model_path(source_model_path, cache_local=args.cache_local)
    try:
        print(
            _run_llama_cpp_python(
                model_path=model_path,
                system_prompt=system_prompt,
                user_prompt=single_prompt,
                max_new_tokens=args.max_new_tokens,
                ctx_size=args.ctx_size,
                temperature=args.temperature,
                threads=args.threads,
            ),
        )
        return
    except Exception as exc:  # noqa: BLE001
        llama_cli_path = _discover_llama_cli(args.llama_cli)
        if llama_cli_path is None:
            raise SystemExit(
                "llama-cpp-python could not load this GGUF package. "
                "Install or point LLAMA_CPP_CLI at llama-cli to use the built-in fallback. "
                f"Original error: {exc}",
            ) from exc
        print(
            f"llama-cpp-python failed; falling back to llama-cli at {llama_cli_path}",
            file=sys.stderr,
        )
        _run_llama_cli(
            llama_cli_path=llama_cli_path,
            model_path=model_path,
            system_prompt=system_prompt,
            user_prompt=single_prompt,
            max_new_tokens=args.max_new_tokens,
            ctx_size=args.ctx_size,
            temperature=args.temperature,
            threads=args.threads,
            reasoning=args.reasoning,
            reasoning_format=args.reasoning_format,
            reasoning_budget=args.reasoning_budget,
        )


if __name__ == "__main__":
    main()
