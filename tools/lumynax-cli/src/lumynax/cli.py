"""LumynaX CLI entry point — `lumynax <command>`."""
from __future__ import annotations
import os, sys, subprocess
from pathlib import Path
from typing import Optional

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


@app.command()
def list(
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
    prompt: str,
    modalities: str = typer.Option("text", help="comma-separated: text,vision,audio"),
    requires_local: bool = typer.Option(False, "--local"),
    tools: bool = typer.Option(False, "--tools"),
    json_out: bool = typer.Option(False, "--json"),
    jurisdiction: str = typer.Option("NZ"),
):
    """Pick the best LumynaX model for a prompt via MaramaRoute scoring."""
    mods = [m.strip() for m in modalities.split(",") if m.strip()]
    candidates = []
    for m in _reg.models():
        if requires_local and m.get("sovereignty_tier", 5) < 3: continue
        if any(mod not in (m.get("modalities") or []) for mod in mods): continue
        if tools and not m.get("supports_tools"): continue
        if json_out and not m.get("supports_json"): continue
        if jurisdiction and jurisdiction not in (m.get("residency") or []): continue
        # score: quality*2 + sov*1.5 + (5-cost)*0.5 + local_bonus
        q = m.get("quality_rank", 5); s = m.get("sovereignty_tier", 3); c = m.get("cost_rank", 5)
        score = (6 - q) * 2 + s * 1.5 + (6 - c) * 0.5
        candidates.append((score, m))
    candidates.sort(key=lambda x: -x[0])
    if not candidates:
        console.print("[red]no candidate matches filters[/red]"); raise typer.Exit(1)
    score, pick = candidates[0]
    console.print(Panel.fit(
        f"[bold]{pick['title']}[/bold]\n"
        f"[cyan]{pick['repo_id']}[/cyan]\n"
        f"score: {score:.2f}\n"
        f"params: {pick.get('total_params_b')}B  · ctx: {pick.get('context_tokens')}\n"
        f"runtime: {pick.get('runtime')}\n\n"
        f"Run with: [yellow]lumynax run {pick['repo_id'].split('/')[-1]}[/yellow] -i",
        title=f"MaramaRoute → top of {len(candidates)} candidates", border_style="yellow",
    ))


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
