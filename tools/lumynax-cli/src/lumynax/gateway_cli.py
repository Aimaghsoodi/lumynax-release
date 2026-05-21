"""lumynax-gateway — wraps Docker Compose + Helm operations for the LumynaX gateway.

Subcommands:
  lumynax-gateway up                    docker compose up -d (single-node)
  lumynax-gateway down                  docker compose down
  lumynax-gateway status                show running services
  lumynax-gateway logs [service]        tail logs
  lumynax-gateway add-model <slug>      append a model server to docker-compose / helm values
  lumynax-gateway helm-install [ns]     helm install lumynax ./deployments/k8s/helm/lumynax
  lumynax-gateway helm-upgrade [ns]     helm upgrade
  lumynax-gateway helm-uninstall [ns]   helm uninstall
  lumynax-gateway audit-tail            tail /audit/gateway.log
"""
from __future__ import annotations
import os, sys, json, subprocess, shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import registry as _reg

app = typer.Typer(name="lumynax-gateway",
                   help="Operate the LumynaX gateway stack (gateway + SearXNG + model servers).",
                   no_args_is_help=True, rich_markup_mode="rich")
console = Console()

ROOT = Path(os.environ.get("LUMYNAX_REPO_ROOT", Path.cwd()))
COMPOSE_FILE = ROOT / "deployments" / "docker-compose.yml"
HELM_DIR     = ROOT / "deployments" / "k8s" / "helm" / "lumynax"


def _run(cmd: list[str], cwd: Optional[Path] = None, check: bool = False) -> int:
    console.print(f"[dim]$ {' '.join(cmd)}[/dim]")
    return subprocess.call(cmd, cwd=str(cwd) if cwd else None)


def _ensure(file: Path, what: str):
    if not file.exists():
        console.print(f"[red]{what} not found at {file}[/red]")
        console.print(f"[yellow]hint:[/yellow] cd into the lumynax-release monorepo, or set LUMYNAX_REPO_ROOT.")
        raise typer.Exit(2)


@app.command()
def up(detach: bool = typer.Option(True, "-d/--no-detach")):
    """docker compose up — bring up gateway + SearXNG + sample model servers."""
    _ensure(COMPOSE_FILE, "docker-compose.yml")
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE), "up"]
    if detach: cmd.append("-d")
    _run(cmd)


@app.command()
def down():
    """docker compose down — tear it all down."""
    _ensure(COMPOSE_FILE, "docker-compose.yml")
    _run(["docker", "compose", "-f", str(COMPOSE_FILE), "down"])


@app.command()
def status():
    """Show running containers + their health."""
    _ensure(COMPOSE_FILE, "docker-compose.yml")
    _run(["docker", "compose", "-f", str(COMPOSE_FILE), "ps"])


@app.command()
def logs(service: Optional[str] = typer.Argument(None), follow: bool = typer.Option(True, "-f/--no-follow")):
    """Tail logs from a service (default: gateway)."""
    _ensure(COMPOSE_FILE, "docker-compose.yml")
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE), "logs"]
    if follow: cmd.append("-f")
    cmd.append(service or "gateway")
    _run(cmd)


@app.command("add-model")
def add_model(slug: str,
              backend: str = typer.Option("llama-cpp", help="llama-cpp | vllm"),
              port: int = typer.Option(8000, help="internal port for the model server")):
    """Append a model server entry to the routes config + print Compose/Helm snippets."""
    m = _reg.find(slug)
    if not m:
        console.print(f"[red]model not found:[/red] {slug}"); raise typer.Exit(2)
    repo_id = m["repo_id"]; slug = repo_id.split("/")[-1]
    svc = f"llama-{slug.replace('lumynax-','')}".lower()
    primary = m.get("primary_artifact") or "model.gguf"
    ctx = int(m.get("context_tokens") or 16384)

    compose_block = f'''
  {svc}:
    image: ghcr.io/ggerganov/llama.cpp:server
    expose: ["{port}"]
    volumes:
      - lumynax-models:/models
    command: >
      --host 0.0.0.0 --port {port} -c {min(ctx,32768)} -ngl -1
      -m /models/AbteeXAILab--{slug}/{primary}
    restart: unless-stopped
''' if backend == "llama-cpp" else f'''
  {svc}:
    image: vllm/vllm-openai:latest
    expose: ["{port}"]
    volumes:
      - lumynax-models:/root/.cache/huggingface
    environment:
      HF_TOKEN: ${{HF_TOKEN}}
    command: >
      --model {repo_id} --port {port} --max-model-len {min(ctx,32768)} --dtype auto
    restart: unless-stopped
'''
    routes_entry = f'"{slug}": "http://{svc}:{port}/v1"'
    console.print(f"\n[bold]Add to deployments/docker-compose.yml under [cyan]services:[/cyan][/bold]")
    console.print(compose_block)
    console.print(f"[bold]Add to deployments/gateway/config/routes.json:[/bold]")
    console.print(f"  {routes_entry}")
    console.print(f"\n[bold]Add to values.yaml under [cyan]modelServers:[/cyan] for Helm:[/bold]")
    console.print(f"""  - name: {slug.replace('lumynax-','')}
    image: ghcr.io/ggerganov/llama.cpp:server
    replicas: 1
    pvcSize: {30 if (m.get('total_params_b') or 0) <= 20 else 60 if (m.get('total_params_b') or 0) <= 50 else 150}Gi
    huggingfaceRepo: "{repo_id}"
    primaryFile: "{primary}"
    contextTokens: {min(ctx, 32768)}
    resources:
      requests: {{ cpu: "2", memory: "{16 if (m.get('total_params_b') or 0) <= 20 else 32}Gi" }}
      limits:   {{ cpu: "8", memory: "{32 if (m.get('total_params_b') or 0) <= 20 else 64}Gi", "nvidia.com/gpu": 1 }}
""")


@app.command("helm-install")
def helm_install(namespace: str = typer.Argument("lumynax")):
    """helm install lumynax ./deployments/k8s/helm/lumynax."""
    _ensure(HELM_DIR / "Chart.yaml", "Helm chart")
    _run(["kubectl", "create", "namespace", namespace])
    _run(["helm", "install", "-n", namespace, "lumynax", str(HELM_DIR)])


@app.command("helm-upgrade")
def helm_upgrade(namespace: str = typer.Argument("lumynax")):
    """helm upgrade lumynax."""
    _ensure(HELM_DIR / "Chart.yaml", "Helm chart")
    _run(["helm", "upgrade", "-n", namespace, "lumynax", str(HELM_DIR)])


@app.command("helm-uninstall")
def helm_uninstall(namespace: str = typer.Argument("lumynax")):
    """helm uninstall lumynax."""
    _run(["helm", "uninstall", "-n", namespace, "lumynax"])


@app.command("audit-tail")
def audit_tail(file: Path = typer.Argument(Path("/audit/gateway.log"))):
    """tail -f the gateway audit log."""
    if not file.exists():
        console.print(f"[yellow]audit log not found at {file}[/yellow]")
        console.print("[yellow]if running in Docker:[/yellow] docker exec lumynax-gateway-1 tail -f /var/log/lumynax/audit.log")
        raise typer.Exit(2)
    _run(["tail", "-f", str(file)])


if __name__ == "__main__":
    app()
