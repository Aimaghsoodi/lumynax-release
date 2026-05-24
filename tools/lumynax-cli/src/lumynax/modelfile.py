"""Modelfile — Ollama-style customization layer for LumynaX.

Syntax (compatible subset of Ollama's Modelfile):

    FROM lumynax-chat-hermes-3-llama31-8b-gguf
    SYSTEM \"\"\"You are a NZ legal research assistant. Cite Acts and case law.\"\"\"
    PARAMETER temperature 0.2
    PARAMETER num_ctx 16384
    PARAMETER top_p 0.9
    PARAMETER stop "</s>"
    TEMPLATE \"\"\"{{ .System }}\n\n{{ .Prompt }}\"\"\"
    LICENSE \"\"\"MIT\"\"\"

Saved derivations live at ~/.lumynax/models/<name>/Modelfile and are surfaced
in `lumynax ls` alongside upstream models.
"""
from __future__ import annotations

import os, re, json, hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from .config import home


@dataclass
class Modelfile:
    base: str
    system: Optional[str] = None
    template: Optional[str] = None
    license: Optional[str] = None
    parameters: dict = field(default_factory=dict)
    # provenance
    source_path: Optional[str] = None
    derived_at: Optional[str] = None

    def to_text(self) -> str:
        lines = [f"FROM {self.base}"]
        if self.system:
            lines.append(f'SYSTEM """{self.system}"""')
        if self.template:
            lines.append(f'TEMPLATE """{self.template}"""')
        for k, v in self.parameters.items():
            if isinstance(v, str): lines.append(f'PARAMETER {k} "{v}"')
            else: lines.append(f'PARAMETER {k} {v}')
        if self.license:
            lines.append(f'LICENSE """{self.license}"""')
        return "\n".join(lines) + "\n"

    def hash(self) -> str:
        return hashlib.sha256(self.to_text().encode()).hexdigest()[:12]


_FROM   = re.compile(r"^\s*FROM\s+([^\s]+)\s*$", re.IGNORECASE | re.MULTILINE)
_SYSTEM = re.compile(r'^\s*SYSTEM\s+"""(.*?)"""', re.IGNORECASE | re.DOTALL | re.MULTILINE)
_TEMPLATE = re.compile(r'^\s*TEMPLATE\s+"""(.*?)"""', re.IGNORECASE | re.DOTALL | re.MULTILINE)
_LICENSE = re.compile(r'^\s*LICENSE\s+"""(.*?)"""', re.IGNORECASE | re.DOTALL | re.MULTILINE)
_PARAM  = re.compile(r'^\s*PARAMETER\s+(\S+)\s+(.+?)\s*$', re.IGNORECASE | re.MULTILINE)


def parse(text: str, source_path: Optional[str] = None) -> Modelfile:
    m = _FROM.search(text)
    if not m:
        raise ValueError("Modelfile must start with a FROM directive")
    mf = Modelfile(base=m.group(1).strip(), source_path=source_path)
    sm = _SYSTEM.search(text);     mf.system   = sm.group(1).strip() if sm else None
    tm = _TEMPLATE.search(text);   mf.template = tm.group(1).strip() if tm else None
    lm = _LICENSE.search(text);    mf.license  = lm.group(1).strip() if lm else None
    for k, v in _PARAM.findall(text):
        v = v.strip()
        if v.startswith('"') and v.endswith('"'): v = v[1:-1]
        else:
            try: v = float(v) if "." in v else int(v)
            except ValueError: pass
        mf.parameters[k.lower()] = v
    return mf


# ---- registry of derived models ----
def models_dir() -> Path:
    d = home() / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_derived(name: str, mf: Modelfile) -> Path:
    """Persist a derived model at ~/.lumynax/models/<name>/Modelfile + metadata.json."""
    safe = re.sub(r"[^a-zA-Z0-9._-]", "-", name).strip("-")
    if not safe: raise ValueError("name must contain at least one alphanumeric")
    out_dir = models_dir() / safe
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "Modelfile").write_text(mf.to_text(), encoding="utf-8")
    meta = {
        "name": safe,
        "base": mf.base,
        "hash": mf.hash(),
        "parameters": mf.parameters,
        "has_system": bool(mf.system),
        "has_template": bool(mf.template),
        "license": mf.license,
    }
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return out_dir


def list_derived() -> list[dict]:
    """Enumerate ~/.lumynax/models/* — all user-derived models."""
    out = []
    for d in sorted(models_dir().iterdir()):
        if not d.is_dir(): continue
        meta_p = d / "metadata.json"
        if meta_p.exists():
            try: out.append(json.loads(meta_p.read_text()))
            except Exception: pass
    return out


def load_derived(name: str) -> Optional[Modelfile]:
    p = models_dir() / name / "Modelfile"
    if not p.exists(): return None
    return parse(p.read_text(encoding="utf-8"), source_path=str(p))


def remove_derived(name: str) -> bool:
    p = models_dir() / name
    if not p.exists(): return False
    import shutil; shutil.rmtree(p)
    return True
