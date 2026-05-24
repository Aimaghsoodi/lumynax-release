"""LumynaX CLI — entry point for the `lumynax` command (Ollama-class CLI for the 98-model family)."""
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
from . import aliases as _aliases
from . import config as _cfg


def _resolve_model(query: str) -> dict:
    """Resolve a query (alias / slug / substring) to a registry entry, or exit cleanly."""
    all_slugs = [m["repo_id"].split("/")[-1] for m in _reg.models()]
    slug, ambig = _aliases.resolve(query, all_slugs)
    if slug:
        for m in _reg.models():
            if m["repo_id"].split("/")[-1] == slug:
                return m
    if ambig:
        Console().print(f"[yellow]ambiguous:[/yellow] '{query}' matches {len(ambig)} models:")
        for s in ambig: Console().print(f"  {s}")
        raise typer.Exit(2)
    # Last fall-back: registry's own find
    m = _reg.find(query)
    if m: return m
    Console().print(f"[red]not found:[/red] {query}")
    raise typer.Exit(2)

app = typer.Typer(
    name="lumynax",
    help=(
        "LumynaX CLI — Ollama-class command-line for the 98-model LumynaX "
        "sovereign-AI release family from AbteeX AI Labs (Aotearoa New Zealand).\n\n"
        "Quick start: 'lumynax list', 'lumynax pull hermes3', 'lumynax run hermes3', "
        "'lumynax route \"fix this bug\"', 'lumynax serve hermes3'."
    ),
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
    """Show full metadata for a single model. Aliases accepted ('hermes3', 'qwen-coder', ...)."""
    m = _resolve_model(model_id)
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
    """Pull a model from Hugging Face (weights + scaffold). Alias of `pull`."""
    pull([model_id], out_dir=out_dir, include_weights=include_weights)


@app.command()
def pull(
    model_ids: List[str] = typer.Argument(..., help="model name(s); aliases ok ('hermes3', 'qwen-coder', etc)"),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", help="local directory (default: ./<slug> each)"),
    include_weights: bool = typer.Option(True, "--weights/--no-weights"),
):
    """Download model(s) from Hugging Face with a live progress bar."""
    from .progress import pull_with_progress
    for q in model_ids:
        m = _resolve_model(q)
        target = out_dir or Path.cwd() / m["repo_id"].split("/")[-1]
        target.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]→[/green] pulling [cyan]{m['repo_id']}[/cyan] → {target}")
        try:
            pull_with_progress(m["repo_id"], target,
                               include_weights=include_weights,
                               token=os.environ.get("HF_TOKEN"))
            console.print(f"[green]✓[/green] {m['repo_id'].split('/')[-1]} ready in {target}")
        except Exception as e:
            console.print(f"[red]✗ pull failed:[/red] {e}")


@app.command()
def run(
    model_id: str,
    prompt: Optional[str] = typer.Argument(None, help="one-shot prompt (omit for REPL)"),
    interactive: bool = typer.Option(True, "-i/--no-interactive", help="REPL mode (default unless --prompt given)"),
    system: Optional[str] = typer.Option(None, "--system", help="system prompt"),
    via_gateway: bool = typer.Option(True, "--gateway/--direct",
                                     help="default: chat through the gateway (slash-cmd REPL); --direct runs the bundled quickstart.py"),
    out_dir: Optional[Path] = typer.Option(None, "--out-dir", help="for --direct: local working dir"),
):
    """Chat with a model. Default: interactive REPL via the gateway (auto-pulls + auto-serves if missing)."""
    m = _resolve_model(model_id)
    slug = m["repo_id"].split("/")[-1]

    if not via_gateway:
        # Legacy mode: run the model's bundled quickstart.py directly
        target = out_dir or Path.cwd() / slug
        if not (target / "quickstart.py").exists():
            pull([model_id], out_dir=target, include_weights=True)
        cmd = [sys.executable, "quickstart.py"]
        if prompt: cmd += ["--prompt", prompt]
        elif interactive: cmd.append("--interactive")
        console.print(f"[green]→[/green] running {target}/quickstart.py")
        subprocess.run(cmd, cwd=target, check=False)
        return

    # Gateway path
    if prompt and not interactive:
        # one-shot
        from .repl import Session
        s = Session(model=slug)
        console.print(f"[green]lumynax>[/green] ", end="")
        s.call(prompt)
        return

    from .repl import run as repl_run
    repl_run(slug, system=system)
    console.print(f"[green]→[/green] running {target}/quickstart.py")
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
    m = _resolve_model(model_id)
    print(json.dumps(_i.opencode(m, base_url=base_url, api_key=api_key), indent=2))


@app.command(name="continue")
def continue_cmd(
    model_id: str,
    base_url: str = typer.Option("http://localhost:8080/v1"),
):
    """Emit a Continue.dev model entry for ~/.continue/config.json."""
    from . import integrations as _i
    import json
    m = _resolve_model(model_id)
    print(json.dumps(_i.continue_dev(m, base_url=base_url), indent=2))


@app.command()
def vllm(model_id: str, port: int = 8000):
    """Emit the vLLM serve command for a LumynaX model."""
    from . import integrations as _i
    m = _resolve_model(model_id)
    if not m: console.print(f"[red]not found:[/red] {model_id}"); raise typer.Exit(2)
    print(_i.vllm_cmd(m, port=port))


@app.command("llama-server")
def llama_server_cmd(model_id: str, port: int = 8080):
    """Emit the llama.cpp `llama-server` command for a LumynaX GGUF model."""
    from . import integrations as _i
    m = _resolve_model(model_id)
    if not m: console.print(f"[red]not found:[/red] {model_id}"); raise typer.Exit(2)
    print(_i.llama_server(m, port=port))


@app.command("lm-studio")
def lm_studio_cmd(model_id: str):
    """Print LM Studio discovery instructions for a LumynaX model."""
    from . import integrations as _i
    m = _resolve_model(model_id)
    if not m: console.print(f"[red]not found:[/red] {model_id}"); raise typer.Exit(2)
    console.print(Panel.fit(_i.lm_studio(m), title=f"LM Studio · {model_id}", border_style="yellow"))


@app.command()
def ollama(model_id: str):
    """Emit Ollama setup commands for a LumynaX model."""
    from . import integrations as _i
    m = _resolve_model(model_id)
    if not m: console.print(f"[red]not found:[/red] {model_id}"); raise typer.Exit(2)
    print(_i.ollama(m))


# ───────────────────── Ollama-class polish (v0.5) ────────────────────────────

@app.command()
def rm(
    model_ids: List[str] = typer.Argument(..., help="slug(s) or alias(es) to delete"),
    yes: bool = typer.Option(False, "-y/--no-yes", help="skip confirmation"),
):
    """Delete locally-downloaded model weights to free disk."""
    import shutil
    for q in model_ids:
        m = _resolve_model(q)
        slug = m["repo_id"].split("/")[-1]
        target = Path.cwd() / slug
        if not target.exists():
            console.print(f"[yellow]not present:[/yellow] {slug} (looked at {target})")
            continue
        size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
        if not yes:
            ok = typer.confirm(f"remove {target} ({size/1e9:.2f} GB)?")
            if not ok: console.print("[dim]skipped[/dim]"); continue
        shutil.rmtree(target)
        console.print(f"[green]✓[/green] removed {target} (freed {size/1e9:.2f} GB)")


@app.command()
def ps():
    """List model servers currently running locally via docker compose."""
    try:
        r = subprocess.run(["docker", "compose", "ps", "--format", "json"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            console.print("[yellow]no docker compose stack in cwd[/yellow]")
            return
        import json
        rows = []
        for line in r.stdout.splitlines():
            try: d = json.loads(line)
            except Exception: continue
            svc = d.get("Service","")
            if svc.startswith("llama-") or svc.startswith("vllm-") or svc == "gateway":
                rows.append(d)
        if not rows:
            console.print("[yellow]no LumynaX services running here[/yellow]"); return
        t = Table(title="Running services")
        for col in ("Service","State","Health","Status"):
            t.add_column(col, style="cyan" if col == "Service" else None)
        for d in rows:
            t.add_row(d.get("Service",""), d.get("State",""), d.get("Health","-"), d.get("Status","")[:60])
        console.print(t)
    except FileNotFoundError:
        console.print("[red]docker not installed on PATH[/red]"); raise typer.Exit(2)


@app.command()
def stop(model_id: str):
    """Stop a specific running model server (gateway stays up)."""
    m = _resolve_model(model_id)
    slug = m["repo_id"].split("/")[-1]
    for prefix in ("llama-", "vllm-"):
        svc = prefix + slug.replace("lumynax-","")[:30]
        r = subprocess.run(["docker","compose","stop", svc], capture_output=True, text=True)
        if r.returncode == 0:
            console.print(f"[green]✓[/green] stopped {svc}"); return
    console.print(f"[yellow]no running container for {slug}[/yellow]")


@app.command()
def aliases(
    add: Optional[str] = typer.Option(None, "--add", help="<short>:<slug-or-alias>"),
):
    """Show alias → slug map; --add to persist a new one to ~/.lumynax/aliases.toml."""
    from . import aliases as _a
    if add:
        if ":" not in add:
            console.print("[red]use --add <short>:<slug>[/red]"); raise typer.Exit(2)
        short, slug = add.split(":", 1)
        m = _resolve_model(slug.strip())
        real = m["repo_id"].split("/")[-1]
        _a.add_alias(short.strip(), real)
        console.print(f"[green]✓[/green] {short} → {real}  (saved to {_a.user_aliases_path()})")
        return
    t = Table(title=f"Aliases ({len(_a.all_aliases())} total)")
    t.add_column("alias", style="cyan"); t.add_column("->"); t.add_column("slug")
    for k, v in sorted(_a.all_aliases().items()):
        t.add_row(k, "->", v)
    console.print(t)


@app.command()
def create(
    name: str = typer.Argument(..., help="name for the derived model (will live at ~/.lumynax/models/<name>)"),
    file: Path = typer.Option(..., "-f", "--file", help="Modelfile path"),
):
    """Create a derived model from a Modelfile (Ollama-style)."""
    from . import modelfile as _mf
    if not file.exists():
        console.print(f"[red]Modelfile not found:[/red] {file}"); raise typer.Exit(2)
    try:
        mf = _mf.parse(file.read_text(encoding="utf-8"), source_path=str(file))
    except Exception as e:
        console.print(f"[red]parse error:[/red] {e}"); raise typer.Exit(2)
    # Verify base exists
    _ = _resolve_model(mf.base)
    out = _mf.save_derived(name, mf)
    console.print(f"[green]✓[/green] derived model '[cyan]{name}[/cyan]' saved → {out}")
    console.print(f"  base:  {mf.base}")
    console.print(f"  hash:  {mf.hash()}")
    console.print(f"  run:   lumynax run {name}")


@app.command()
def cp(
    source: str = typer.Argument(..., help="existing model (alias/slug)"),
    dest: str = typer.Argument(..., help="new derived-model name"),
    system: Optional[str] = typer.Option(None, "--system", help="set/override system prompt"),
    temperature: Optional[float] = typer.Option(None, "--temperature"),
    num_ctx: Optional[int] = typer.Option(None, "--num-ctx"),
):
    """Copy a model to a new derived name with optional parameter overrides."""
    from . import modelfile as _mf
    m = _resolve_model(source)
    base = m["repo_id"].split("/")[-1]
    mf = _mf.Modelfile(base=base)
    if system is not None:      mf.system = system
    if temperature is not None: mf.parameters["temperature"] = temperature
    if num_ctx is not None:     mf.parameters["num_ctx"] = num_ctx
    out = _mf.save_derived(dest, mf)
    console.print(f"[green]✓[/green] copied {base} → {dest} ({out})")


@app.command()
def show_modelfile(name: str):
    """Print the Modelfile of a derived model."""
    from . import modelfile as _mf
    mf = _mf.load_derived(name)
    if not mf: console.print(f"[red]no derived model:[/red] {name}"); raise typer.Exit(2)
    from rich.syntax import Syntax
    console.print(Syntax(mf.to_text(), "dockerfile", theme="monokai", line_numbers=False))


@app.command()
def config_show():
    """Show effective config (~/.lumynax/config.toml + env)."""
    import dataclasses
    c = _cfg.load()
    t = Table(title=f"Config — {_cfg.config_path()}")
    t.add_column("key", style="cyan"); t.add_column("value")
    for k, v in dataclasses.asdict(c).items(): t.add_row(k, str(v))
    console.print(t)


@app.command()
def config_set(key: str, value: str):
    """Set a config key in ~/.lumynax/config.toml."""
    c = _cfg.load()
    if not hasattr(c, key):
        console.print(f"[red]unknown key:[/red] {key}"); raise typer.Exit(2)
    cur = getattr(c, key)
    new_val: object = value
    if isinstance(cur, bool):   new_val = value.lower() in ("true","1","yes","on")
    elif isinstance(cur, int):  new_val = int(value)
    elif isinstance(cur, float): new_val = float(value)
    setattr(c, key, new_val)
    _cfg.save(c)
    console.print(f"[green]✓[/green] {key} = {new_val}  (saved to {_cfg.config_path()})")


@app.command()
def completion(shell: str = typer.Argument("bash", help="bash | zsh | fish")):
    """Emit a shell-completion script. Source it from your rc file."""
    if shell == "bash":
        print("# Add to ~/.bashrc:  eval \"$(_LUMYNAX_COMPLETE=bash_source lumynax)\"")
        print('eval "$(_LUMYNAX_COMPLETE=bash_source lumynax)"')
    elif shell == "zsh":
        print("# Add to ~/.zshrc:  eval \"$(_LUMYNAX_COMPLETE=zsh_source lumynax)\"")
        print('eval "$(_LUMYNAX_COMPLETE=zsh_source lumynax)"')
    elif shell == "fish":
        print("# Add to ~/.config/fish/completions/lumynax.fish:")
        print('eval (env _LUMYNAX_COMPLETE=fish_source lumynax)')
    else:
        console.print(f"[red]unknown shell:[/red] {shell}"); raise typer.Exit(2)


@app.command(name="version")
def version_cmd():
    """Print version and exit."""
    print(f"lumynax {__version__}")


if __name__ == "__main__":
    app()
