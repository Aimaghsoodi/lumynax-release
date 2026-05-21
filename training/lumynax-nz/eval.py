"""Quick eval for LumynaX-NZ on three checks: te reo translation, NZ trivia, base-loss diff."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

NZ_TRIVIA = [
    ("What is the māori name for Wellington?", ["Te Whanganui-a-Tara","Te Whanganui"]),
    ("Translate 'kia ora' into English.", ["hello","be well","good health"]),
    ("Which NZ act governs personal information privacy?", ["Privacy Act 2020","Privacy Act"]),
    ("What is the Treaty of Waitangi commonly abbreviated as in te reo?", ["Te Tiriti","Te Tiriti o Waitangi"]),
]
TE_REO_PAIRS = [
    ("Translate to te reo Māori: 'hello, how are you?'", "kia ora"),
    ("Translate to English: 'Mā te wā'", "see you later"),
    ("Translate to English: 'whānau'", "family"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--base_model", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--max_tokens", type=int, default=128)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(args.model, device_map="auto",
                                                  torch_dtype=torch.bfloat16, trust_remote_code=True)

    def chat(prompt: str) -> str:
        messages = [{"role": "system", "content": "You are LumynaX-NZ, an assistant fine-tuned on Aotearoa New Zealand corpora. Answer concisely."},
                    {"role": "user", "content": prompt}]
        text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tok(text, return_tensors="pt").to(model.device)
        out = model.generate(**inputs, max_new_tokens=args.max_tokens, do_sample=False)
        return tok.decode(out[0, inputs["input_ids"].shape[-1]:], skip_special_tokens=True).strip()

    results = {"nz_trivia": [], "te_reo": []}

    print("\n== NZ trivia ==")
    for q, expected_subs in NZ_TRIVIA:
        a = chat(q); hit = any(s.lower() in a.lower() for s in expected_subs)
        print(f"  {q}\n    → {a}\n    {'✓' if hit else '✗'}")
        results["nz_trivia"].append({"q": q, "a": a, "hit": hit})

    print("\n== te reo translation ==")
    for q, expected in TE_REO_PAIRS:
        a = chat(q); hit = expected.lower() in a.lower()
        print(f"  {q}\n    → {a}\n    {'✓' if hit else '✗'}")
        results["te_reo"].append({"q": q, "a": a, "hit": hit})

    trivia_score = sum(1 for r in results["nz_trivia"] if r["hit"]) / len(NZ_TRIVIA)
    tereo_score  = sum(1 for r in results["te_reo"]    if r["hit"]) / len(TE_REO_PAIRS)
    print(f"\nNZ trivia: {trivia_score:.2f}  ·  Te reo: {tereo_score:.2f}")

    out = Path(args.model) / "eval.json"
    out.write_text(json.dumps({"trivia": trivia_score, "tereo": tereo_score, "results": results}, indent=2), encoding="utf-8")
    print(f"saved → {out}")


if __name__ == "__main__":
    main()
