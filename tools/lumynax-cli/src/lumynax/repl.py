"""Interactive REPL — `lumynax run <model>`.

Slash commands:
  /clear              Clear conversation history
  /save <file>        Save history to a JSON file
  /load <file>        Replace history with a JSON file
  /show               Show current model + session info
  /set <key> <val>    Set a session parameter (temperature, max_tokens, system)
  /system <text>      Replace the system prompt
  /tools on|off       Toggle web_search tool injection
  /switch <model>     Hot-swap to a different model (history preserved)
  /multiline          Enter multi-line input mode (end with '''.''')
  /?  or  /help       This help
  /exit, /quit, /q    Leave (Ctrl-D also works)
"""
from __future__ import annotations

import json, os, sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from .config import load as load_config


console = Console()


@dataclass
class Session:
    model: str
    history: list[dict] = field(default_factory=list)
    system: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1024
    web_search: bool = False
    gateway_url: str = "http://localhost:8080/v1"
    api_key: str = "lumynax-local-dev"

    @property
    def messages(self) -> list[dict]:
        out = []
        if self.system:
            out.append({"role": "system", "content": self.system})
        out.extend(self.history)
        return out

    def call(self, user_msg: str, stream: bool = True) -> str:
        self.history.append({"role": "user", "content": user_msg})
        body = {
            "model": self.model, "messages": self.messages,
            "temperature": self.temperature, "max_tokens": self.max_tokens,
            "stream": stream,
        }
        if self.web_search: body["enable_web_search"] = True
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        url = f"{self.gateway_url.rstrip('/')}/chat/completions"
        try:
            if stream:
                buf = []
                with httpx.stream("POST", url, headers=headers, json=body, timeout=600) as r:
                    if r.status_code >= 400:
                        msg = r.read().decode("utf-8", errors="ignore")[:300]
                        raise RuntimeError(f"{r.status_code}: {msg}")
                    for line in r.iter_lines():
                        if not line.startswith("data:"): continue
                        payload = line[5:].strip()
                        if payload == "[DONE]": break
                        try:
                            d = json.loads(payload)
                            delta = d["choices"][0].get("delta", {}).get("content", "")
                            if delta:
                                console.print(delta, end="", style="green", soft_wrap=True)
                                buf.append(delta)
                        except Exception: pass
                console.print()
                reply = "".join(buf)
            else:
                r = httpx.post(url, headers=headers, json=body, timeout=600)
                r.raise_for_status()
                reply = r.json()["choices"][0]["message"]["content"]
                console.print(reply, style="green")
            self.history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e:
            self.history.pop()  # roll back the user message
            console.print(f"[red]error:[/red] {e}")
            return ""


SLASH_HELP = """[bold]Slash commands[/bold]
  /clear              clear history
  /save <file>        save history JSON
  /load <file>        replace history from JSON
  /show               session info
  /set <k> <v>        temperature | max_tokens | system | gateway_url
  /system <text>      replace system prompt
  /tools on|off       toggle web_search tool injection
  /switch <model>     hot-swap to another model
  /multiline          multi-line input mode (terminate with a single '.')
  /? /help            this help
  /exit /quit /q      leave (Ctrl-D also exits)
"""


def run(model_slug: str,
        gateway_url: Optional[str] = None,
        api_key: Optional[str] = None,
        system: Optional[str] = None) -> None:
    cfg = load_config()
    s = Session(
        model=model_slug,
        gateway_url=(gateway_url or cfg.gateway_url + "/v1") if gateway_url else cfg.gateway_url + "/v1",
        api_key=api_key or cfg.api_key,
        system=system,
    )
    console.print(Panel.fit(
        f"[bold]chat with [cyan]{model_slug}[/cyan][/bold]\n"
        f"gateway: {s.gateway_url}\n"
        f"type your message, [green]enter[/green] to send · [yellow]/?[/yellow] for slash commands · [red]Ctrl-D[/red] to quit",
        border_style="yellow", title="LumynaX",
    ))

    while True:
        try:
            line = console.input("[blue]you>[/blue] ")
        except (EOFError, KeyboardInterrupt):
            console.print(); break

        if not line.strip(): continue
        if line.startswith("/"):
            if _handle_slash(line.strip(), s): continue
            else: break

        console.print("[green]lumynax>[/green] ", end="")
        s.call(line)


def _handle_slash(cmd: str, s: Session) -> bool:
    """Returns False if REPL should exit, True otherwise."""
    parts = cmd.split(maxsplit=2)
    op = parts[0].lower()

    if op in ("/exit", "/quit", "/q", "/bye"): return False
    if op in ("/help", "/?"):
        console.print(Panel.fit(SLASH_HELP, border_style="yellow", title="slash commands"))
        return True
    if op == "/clear":
        s.history.clear()
        console.print("[dim]history cleared[/dim]"); return True
    if op == "/show":
        info = (
            f"model:        {s.model}\n"
            f"messages:     {len(s.history)}\n"
            f"system:       {s.system or '(none)'}\n"
            f"temperature:  {s.temperature}\n"
            f"max_tokens:   {s.max_tokens}\n"
            f"web_search:   {s.web_search}\n"
            f"gateway:      {s.gateway_url}\n"
        )
        console.print(Panel.fit(info, border_style="cyan", title="session"))
        return True
    if op == "/save":
        if len(parts) < 2: console.print("[red]usage:[/red] /save <file>"); return True
        path = Path(parts[1]).expanduser()
        path.write_text(json.dumps({"model": s.model, "system": s.system, "history": s.history}, indent=2))
        console.print(f"[dim]saved {len(s.history)} messages → {path}[/dim]")
        return True
    if op == "/load":
        if len(parts) < 2: console.print("[red]usage:[/red] /load <file>"); return True
        path = Path(parts[1]).expanduser()
        if not path.exists(): console.print(f"[red]not found:[/red] {path}"); return True
        try:
            d = json.loads(path.read_text())
            s.history = d.get("history") or []
            if d.get("system"): s.system = d["system"]
            console.print(f"[dim]loaded {len(s.history)} messages from {path}[/dim]")
        except Exception as e:
            console.print(f"[red]load failed:[/red] {e}")
        return True
    if op == "/set":
        if len(parts) < 3: console.print("[red]usage:[/red] /set <key> <value>"); return True
        k, v = parts[1].lower(), parts[2]
        if k == "temperature":
            try: s.temperature = float(v)
            except ValueError: console.print("[red]temperature must be a float[/red]"); return True
        elif k == "max_tokens":
            try: s.max_tokens = int(v)
            except ValueError: console.print("[red]max_tokens must be an int[/red]"); return True
        elif k == "system":
            s.system = v
        elif k == "gateway_url":
            s.gateway_url = v
        else:
            console.print(f"[red]unknown key:[/red] {k} (try temperature, max_tokens, system, gateway_url)")
            return True
        console.print(f"[dim]set {k} = {v}[/dim]")
        return True
    if op == "/system":
        s.system = " ".join(parts[1:]) or None
        console.print(f"[dim]system prompt {'set' if s.system else 'cleared'}[/dim]")
        return True
    if op == "/tools":
        v = (parts[1].lower() if len(parts) > 1 else "")
        if v in ("on","true","1","yes"): s.web_search = True
        elif v in ("off","false","0","no"): s.web_search = False
        else: console.print("[red]usage:[/red] /tools on|off"); return True
        console.print(f"[dim]web_search = {s.web_search}[/dim]")
        return True
    if op == "/switch":
        if len(parts) < 2: console.print("[red]usage:[/red] /switch <model>"); return True
        s.model = parts[1]
        console.print(f"[dim]now chatting with [cyan]{s.model}[/cyan][/dim]")
        return True
    if op == "/multiline":
        console.print("[dim]multi-line: terminate with a single '.' on its own line[/dim]")
        lines = []
        while True:
            try:
                ln = input("... ")
            except (EOFError, KeyboardInterrupt):
                return True
            if ln.strip() == ".": break
            lines.append(ln)
        body = "\n".join(lines).strip()
        if body:
            console.print("[green]lumynax>[/green] ", end="")
            s.call(body)
        return True

    console.print(f"[red]unknown slash command:[/red] {op}   (try /?)")
    return True
