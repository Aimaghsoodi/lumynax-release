"""LumynaX CLI entry point — `lumynax <command>`."""
from __future__ import annotations
import os, sys, subprocess
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from . import __version__
from . import registry as _reg

app = typer.Typer(
    name="lumynax",
    help="LumynaX CLI — sovereign-AI release family from AbteeX AI Labs (Aotearoa New Zealand).",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"lumynax {__version__}")
        raise typer.Exit()


@app.callback()
def _root(version: bool = typer.Option(False, "--version", "-V", callback=_version_callback, is_eager=True)):
    pass


@app.command("list")
def _list_cmd(
    tier: Optional[str] = typer.Option(None, help="frontier|multimodal|reasoning|coder|embed|moe|speech|doc|guard|chat|translate|tiny"),
    modality: Optional[str] = typer.Option(None, help="text|vision|audio"),
    max_params: Optional[float] = typer.Option(None, "--max-params-b", help="max total params (billions)"),
    tools: Optional[bool] = typer.Option(None, "--tools/--no-tools", help="require tool-calling support"),
    jurisdiction: Optional[str] = typer.Option(None, help="filter to models routable in NZ/AU/global"),
):
    """List models in the registry, with optional filters."""
    rows = _reg.filter_by(tier=tier, modality=modality, max_params_b=max_params, supports_tools=tools, jurisdiction=jurisdiction)
    t = Table(title=f"LumynaX models ({len(rows)} of {len(_reg.models())})", show_lines=False)
    t.add_column("slug", style="cyan")
    t.add_column("params", justify="right")
    t.add_column("ctx", justify="right")
    t.add_column("modalities")
    t.add_column("tier", justify="right")
    t.add_column("license")
    for m in rows:
        tp = m.get("total_params_b"); ap = m.get("active_params_b")
        p = f"{tp}B" + (f"/{ap}Ba" if ap else "") if tp else "—"
        t.add_row(
            m["repo_id"].split("/")[-1],
            p, str(m.get("context_tokens") or "—"),
            ",".join(m.get("modalities") or []),
            str(m.get("sovereignty_tier") or "—"),
            m.get("license_id", "—"),
        )
    console.print(t)


@app.command()
def info(model_id: str):
    """Show full metadata for a single model."""
    m = _reg.find(model_id)
    if not m:
        console.print(f"[red]not found:[/red] {model_id}")
        raise typer.Exit(2)
    console.print(Panel.fit(
        f"[bold]{m['title']}[/bold]\n"
        f"[cyan]{m['repo_id']}[/cyan]\n\n"
        f"Family:        {m.get('family')}\n"
        f"Runtime:       {m.get('runtime')}\n"
        f"Modalities:    {', '.join(m.get('modalities') or [])}\n"
        f"Total params:  {m.get('total_params_b')}B  (active {m.get('active_params_b') or '—'}B)\n"
        f"Context:       {m.get('context_tokens')} tokens\n"
        f"Quantization:  {m.get('quantization')}\n"
        f"Primary file:  {m.get('primary_artifact')}\n"
        f"License:       {m.get('license_id')}\n"
        f"Jurisdiction:  {m.get('jurisdiction')}  ({', '.join(m.get('residency') or [])})\n"
        f"Sovereignty:   tier {m.get('sovereignty_tier')}\n"
        f"Tools/JSON:    {m.get('supports_tools')} / {m.get('supports_json')}\n"
        f"Upstream:      {m.get('metadata',{}).get('upstream_repo')}\n",
        title=m["repo_id"], border_style="yellow",
    ))


@app.command()
def download(
    model_id: str,
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", help="local directory (default: ./<slug>)"),
    include_weights: bool = typer.Option(True, "--weights/--no-weights", help="include weight files"),
):
    """Pull a model from Hugging Face (weights + scaffold)."""
    m = _reg.find(model_id)
    if not m:
        console.print(f"[red]not found:[/red] {model_id}"); raise typer.Exit(2)
    target = out_dir or Path.cwd() / m["repo_id"].split("/")[-1]
    target.mkdir(parents=True, exist_ok=True)
    from huggingface_hub import snapshot_download
    allow = None if include_weights else ["README.md","quickstart.py","requirements.txt","LICENSE*","docs/*.svg","ollama/Modelfile","release_export_manifest.json"]
    console.print(f"[green]→[/green] downloading {m['repo_id']} to {target}")
    snapshot_download(repo_id=m["repo_id"], local_dir=str(target), allow_patterns=allow,
                       token=os.environ.get("HF_TOKEN"))
    console.print(f"[green]✓[/green] done. cd {target} && pip install -r requirements.txt && python quickstart.py")


@app.command()
def run(
    model_id: str,
    prompt: str = typer.Argument("Explain LumynaX in 2 bullets.", help="prompt to run"),
    interactive: bool = typer.Option(False, "-i", "--interactive"),
    out_dir: Optional[Path] = typer.Option(None, help="working dir (will hf-download if absent)"),
):
    """Download (if needed) and run a model's quickstart.py."""
    m = _reg.find(model_id)
    if not m:
        console.print(f"[red]not found:[/red] {model_id}"); raise typer.Exit(2)
    target = out_dir or Path.cwd() / m["repo_id"].split("/")[-1]
    if not (target / "quickstart.py").exists():
        download.callback(model_id, out_dir=target, include_weights=True)
    cmd = [sys.executable, "quickstart.py"]
    if interactive: cmd.append("--interactive")
    else: cmd += ["--prompt", prompt]
    console.print(f"[green]→[/green] running {target}/quickstart.py")
    subprocess.run(cmd, cwd=target, check=False)


@app.command()
def route(
    prompt: Optional[str] = typer.Argument(None, help="Prompt (or '-' / stdin pipe). The router will analyze it."),
    modalities: str = typer.Option("text", help="comma-separated: text,vision,audio (auto-detected if prompt given)"),
    strategy: str = typer.Option("balanced", help="balanced | cheap | frontier | local-only | coder | vision | reasoning | te-reo"),
    requires_local: bool = typer.Option(False, "--local", help="force sovereignty tier ≥ 3"),
    tools: Optional[bool] = typer.Option(None, "--tools/--no-tools", help="require tool-calling (auto-detected by default)"),
    json_mode: Optional[bool] = typer.Option(None, "--json-mode/--no-json-mode", help="require JSON mode (auto-detected)"),
    jurisdiction: str = typer.Option("NZ"),
    max_params: float = typer.Option(0.0, "--max-params-b", help="max total params (B); 0 = unlimited"),
    min_context: int = typer.Option(0, "--min-ctx", help="minimum context tokens required"),
    prefer_family: Optional[str] = typer.Option(None, "--prefer-family"),
    forbid: Optional[List[str]] = typer.Option(None, "--forbid", help="slug(s) to exclude; can repeat"),
    output: str = typer.Option("pretty", "--format", "-f", help="pretty | json | slug | openai-stub"),
    explain: bool = typer.Option(False, "--explain", help="also show prompt analysis + score breakdown"),
    compare: int = typer.Option(0, "--compare", "-c", help="show top-N comparison table"),
    why_not_slug: Optional[str] = typer.Option(None, "--why-not", help="explain why a specific slug was not picked"),
    show_rejected: int = typer.Option(0, "--show-rejected", help="show N rejection reasons"),
    gateway_url: str = typer.Option("http://localhost:8080/v1", help="for --format openai-stub"),
):
    """Pick the best LumynaX model for a prompt via MaramaRoute scoring.

    The router auto-detects code, vision, audio, math, te-reo, and long-context
    intents from your prompt. Use --strategy to bias the scoring.

    Examples:
      lumynax route "fix this Python bug"
      lumynax route --strategy frontier "explain transformers"
      lumynax route --strategy te-reo "translate to Maori: hello"
      lumynax route --strategy cheap --local --max-params-b 10 "summarize this"
      cat code.py | lumynax route -
      lumynax route "do X" --format slug | xargs -I {} lumynax run {} -i
    """
    from .router import Router, Strategy
    from .router import explain as render
    import sys

    # Stdin support
    if prompt == "-" or (prompt is None and not sys.stdin.isatty()):
        prompt = sys.stdin.read()
    elif prompt is None:
        prompt = ""

    try:
        strat = Strategy(strategy)
    except ValueError:
        console.print(f"[red]unknown strategy '{strategy}'[/red] — choose: {[s.value for s in Strategy]}")
        raise typer.Exit(2)

    mods = [m.strip() for m in modalities.split(",") if m.strip()]
    router = Router(models=_reg.models())
    d = router.route(
        prompt=prompt,
        modalities=mods,
        requires_local=requires_local,
        requires_tools=tools,
        requires_json=json_mode,
        jurisdiction=jurisdiction,
        max_params_b=max_params,
        min_context=min_context,
        strategy=strat,
        prefer_family=prefer_family,
        forbid_slugs=forbid,
    )

    if why_not_slug:
        console.print(render.why_not(d, why_not_slug))
        raise typer.Exit(0 if d.pick else 1)

    if compare > 0:
        render.compare_top(d, n=compare)
        raise typer.Exit(0 if d.pick else 1)

    if output == "json":
        print(render.as_json(d))
    elif output == "slug":
        print(render.slug_only(d))
    elif output == "openai-stub":
        print(render.openai_stub(d, gateway_url=gateway_url))
    else:
        render.pretty(d, show_analysis=explain, show_rejected=show_rejected)

    raise typer.Exit(0 if d.pick else 1)


@app.command()
def refresh():
    """Re-fetch the registry from Hugging Face."""
    reg = _reg.load(force_refresh=True)
    console.print(f"[green]✓[/green] refreshed: {len(reg['models'])} models")


@app.command()
def serve(
    model_id: str,
    port: int = typer.Option(8080),
    host: str = typer.Option("127.0.0.1"),
    backend: Optional[str] = typer.Option(None, help="llama-cpp | vllm (default: auto)"),
    ctx: Optional[int] = typer.Option(None, "--ctx", help="override context length"),
    n_gpu_layers: int = typer.Option(-1, "--n-gpu-layers"),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", help="local weights dir"),
):
    """Start an OpenAI-compatible HTTP server for any LumynaX model."""
    from .serve import serve as _do_serve
    _do_serve(model_id, port=port, host=host, backend=backend, ctx=ctx,
              n_gpu_layers=n_gpu_layers, out_dir=out_dir)


@app.command()
def opencode(
    model_id: str,
    base_url: str = typer.Option("http://localhost:8080/v1"),
    api_key: str = typer.Option("lumynax-local"),
):
    """Emit an OpenCode provider config for a LumynaX model (JSON to stdout)."""
    from . import integrations as _i
    import json
    m = _reg.find(model_id)
    if not m:
        console.print(f"[red]not found:[/red] {model_id}"); raise typer.Exit(2)
    print(json.dumps(_i.opencode(m, base_url=base_url, api_key=api_key), indent=2))


@app.command(name="continue")
def continue_cmd(
    model_id: str,
    base_url: str = typer.Option("http://localhost:8080/v1"),
):
    """Emit a Continue.dev model entry for ~/.continue/config.json."""
    from . import integrations as _i
    import json
    m = _reg.find(model_id)
    if not m:
        console.print(f"[red]not found:[/red] {model_id}"); raise typer.Exit(2)
    print(json.dumps(_i.continue_dev(m, base_url=base_url), indent=2))


@app.command()
def vllm(model_id: str, port: int = 8000):
    """Emit the vLLM serve command for a LumynaX model."""
    from . import integrations as _i
    m = _reg.find(model_id)
    if not m: console.print(f"[red]not found:[/red] {model_id}"); raise typer.Exit(2)
    print(_i.vllm_cmd(m, port=port))


@app.command("llama-server")
def llama_server_cmd(model_id: str, port: int = 8080):
    """Emit the llama.cpp `llama-server` command for a LumynaX GGUF model."""
    from . import integrations as _i
    m = _reg.find(model_id)
    if not m: console.print(f"[red]not found:[/red] {model_id}"); raise typer.Exit(2)
    print(_i.llama_server(m, port=port))


@app.command("lm-studio")
def lm_studio_cmd(model_id: str):
    """Print LM Studio discovery instructions for a LumynaX model."""
    from . import integrations as _i
    m = _reg.find(model_id)
    if not m: console.print(f"[red]not found:[/red] {model_id}"); raise typer.Exit(2)
    console.print(Panel.fit(_i.lm_studio(m), title=f"LM Studio · {model_id}", border_style="yellow"))


@app.command()
def ollama(model_id: str):
    """Emit Ollama setup commands for a LumynaX model."""
    from . import integrations as _i
    m = _reg.find(model_id)
    if not m: console.print(f"[red]not found:[/red] {model_id}"); raise typer.Exit(2)
    print(_i.ollama(m))


if __name__ == "__main__":
    app()
