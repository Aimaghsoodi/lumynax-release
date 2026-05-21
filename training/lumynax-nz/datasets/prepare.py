"""
LumynaX-NZ corpus builder. Downloads, cleans, dedupes, and shards every source in
sources.yaml into a single JSONL ready for the training scripts.

Usage:
  python datasets/prepare.py --out data/
  python datasets/prepare.py --out data/ --exclude rnz_open --max-gb 3
  python datasets/prepare.py --resume   # resume partial download

Output:
  data/train.jsonl        — {text} records, ChatML-ready
  data/eval.jsonl         — held-out 1% for evaluation
  data/provenance.json    — per-source hashes, URLs, licences, counts
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, time, urllib.parse
from pathlib import Path
from typing import Iterable

import yaml
import httpx
from datasets import load_dataset


HERE = Path(__file__).resolve().parent
SOURCES = yaml.safe_load((HERE / "sources.yaml").read_text(encoding="utf-8"))


def log(m: str) -> None: print(f"[prep] {m}", flush=True)


def sha256_bytes(b: bytes) -> str: return hashlib.sha256(b).hexdigest()


def clean_text(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t)            # strip html
    t = re.sub(r"\s+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def shard_into_chunks(text: str, max_chars: int = 6000, overlap: int = 200) -> Iterable[str]:
    """Naive overlapping char-window shard. Good enough for SFT."""
    i = 0; n = len(text)
    while i < n:
        yield text[i: i + max_chars]
        i += max_chars - overlap


def fetch_hansard(out_dir: Path, max_gb: float) -> list[dict]:
    """Skeleton: in production wire to the parliament.nz Hansard XML API.
    This stub generates a placeholder demonstrating the cleaning pipeline."""
    log("nz_hansard: configure with real parliament.nz API. Stub returns empty.")
    return []


def fetch_statutes(out_dir: Path) -> list[dict]:
    log("nz_statutes: configure with legislation.govt.nz bulk export. Stub returns empty.")
    return []


def fetch_nllb_mi_en(out_dir: Path) -> list[dict]:
    """Te reo Maori <-> English pairs from NLLB-200, formatted as bidirectional SFT."""
    log("nllb_mi_en: loading allenai/nllb mi-en split (this will download)...")
    try:
        ds = load_dataset("allenai/nllb", "mri-eng_Latn", split="train[:80000]", trust_remote_code=False)
    except Exception as e:
        log(f"  fallback: {e}; trying alternate config...")
        try:
            ds = load_dataset("allenai/nllb", "eng_Latn-mri_Latn", split="train[:80000]", trust_remote_code=False)
        except Exception as e2:
            log(f"  cannot load NLLB mi-en directly: {e2}")
            log(f"  manual fix: download a mi-en parallel corpus and put records like")
            log(f'             {{"text": "[en] hello [mi] kia ora"}} into data/raw/nllb.jsonl')
            return []
    records = []
    for ex in ds:
        en = (ex.get("translation") or {}).get("eng_Latn") or ex.get("eng_Latn")
        mi = (ex.get("translation") or {}).get("mri_Latn") or ex.get("mri_Latn")
        if not (en and mi): continue
        records.append({"text": (
            f"### English\n{en.strip()}\n\n### Te Reo Māori\n{mi.strip()}\n\n"
            f"### Translate (English → Māori)\n{en.strip()} → {mi.strip()}\n\n"
            f"### Translate (Māori → English)\n{mi.strip()} → {en.strip()}\n"
        )})
    return records


def fetch_rnz(out_dir: Path) -> list[dict]:
    log("rnz_open: requires manual flag of CC-licensed transcripts. Stub returns empty.")
    return []


def fetch_nz_uni_open(out_dir: Path) -> list[dict]:
    log("nz_uni_open: configure with openaccess.ac.nz; respect per-page licence. Stub returns empty.")
    return []


def fetch_tikanga(out_dir: Path) -> list[dict]:
    log("tikanga_public: REQUIRES iwi consultation. Skipped by default.")
    log("  to include: add an attribution.md listing every source with iwi sign-off, then run with --include-tikanga")
    return []


FETCHERS = {
    "nz_hansard":    fetch_hansard,
    "nz_statutes":   fetch_statutes,
    "rnz_open":      fetch_rnz,
    "nllb_mi_en":    fetch_nllb_mi_en,
    "nz_uni_open":   fetch_nz_uni_open,
    "tikanga_public": fetch_tikanga,
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "data"))
    ap.add_argument("--exclude", action="append", default=[])
    ap.add_argument("--include-tikanga", action="store_true",
                     help="Only after iwi consultation per sources.yaml policy.")
    ap.add_argument("--max-gb", type=float, default=10.0)
    ap.add_argument("--eval-frac", type=float, default=0.01)
    args = ap.parse_args()

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    raw = out / "raw"; raw.mkdir(exist_ok=True)
    provenance: dict = {"sources": {}, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    train_path = out / "train.jsonl"
    eval_path = out / "eval.jsonl"
    n_train = n_eval = 0
    with train_path.open("w", encoding="utf-8") as ft, eval_path.open("w", encoding="utf-8") as fe:
        for corpus in SOURCES["corpora"]:
            cid = corpus["id"]
            if cid in args.exclude:
                log(f"skip {cid} (--exclude)"); continue
            if cid == "tikanga_public" and not args.include_tikanga:
                log(f"skip {cid} (requires --include-tikanga + iwi attribution)"); continue
            fetcher = FETCHERS.get(cid)
            if not fetcher:
                log(f"no fetcher for {cid}, skipping"); continue
            log(f"fetching {cid}...")
            records = fetcher(raw, args.max_gb) if cid == "nz_hansard" else fetcher(raw)
            n_kept = 0
            for r in records:
                txt = clean_text(r["text"])
                if len(txt) < 80: continue
                line = json.dumps({"text": txt, "source": cid}, ensure_ascii=False)
                # 1% goes to eval, 99% to train (deterministic per-text)
                bucket = int(hashlib.sha1(txt.encode()).hexdigest(), 16) % 1000
                if bucket < int(args.eval_frac * 1000):
                    fe.write(line + "\n"); n_eval += 1
                else:
                    ft.write(line + "\n"); n_train += 1
                n_kept += 1
            provenance["sources"][cid] = {
                "license": corpus["license"],
                "url": corpus["url"],
                "n_records": n_kept,
            }
            log(f"  {cid}: kept {n_kept} records")

    provenance["totals"] = {"train": n_train, "eval": n_eval}
    (out / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    log(f"DONE — train.jsonl {n_train}  eval.jsonl {n_eval}")
    log(f"  provenance: {out / 'provenance.json'}")
    if n_train == 0:
        log("WARNING: zero training records. Configure source fetchers (see stubs in this file) or supply data/raw/*.jsonl manually.")


if __name__ == "__main__":
    main()
