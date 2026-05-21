"""MMLU runner — 5-shot, accuracy."""
import argparse, json, sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common.client import GatewayClient, save_result
from datasets import load_dataset


PROMPT = """The following is a multiple-choice question. Answer with the single letter (A/B/C/D) only.

{shots}
Question: {question}
A) {a}
B) {b}
C) {c}
D) {d}
Answer:"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--gateway", default="http://localhost:8080/v1")
    ap.add_argument("--key", default="lumynax-local-dev")
    ap.add_argument("--subjects", nargs="+", default=None, help="subset of MMLU subjects")
    ap.add_argument("--limit-per-subject", type=int, default=20)
    args = ap.parse_args()

    client = GatewayClient(base_url=args.gateway, api_key=args.key)
    ds = load_dataset("cais/mmlu", "all", split="test", trust_remote_code=False)
    dev = load_dataset("cais/mmlu", "all", split="dev", trust_remote_code=False)
    subjects = args.subjects or sorted(set(ds["subject"]))

    correct = total = 0
    per_subject = {}
    for subj in subjects:
        items = [r for r in ds if r["subject"] == subj][: args.limit_per_subject]
        dev_items = [r for r in dev if r["subject"] == subj][:5]
        shots = "\n\n".join(
            f"Question: {d['question']}\nA) {d['choices'][0]}\nB) {d['choices'][1]}\nC) {d['choices'][2]}\nD) {d['choices'][3]}\nAnswer: {'ABCD'[d['answer']]}"
            for d in dev_items
        )
        s_correct = 0
        for r in items:
            prompt = PROMPT.format(shots=shots + "\n\n" if shots else "",
                                    question=r["question"],
                                    a=r["choices"][0], b=r["choices"][1], c=r["choices"][2], d=r["choices"][3])
            out = client.chat(args.model, [{"role": "user", "content": prompt}],
                               temperature=0.0, max_tokens=4).strip().upper()
            answer = next((ch for ch in out if ch in "ABCD"), "")
            ok = (answer == "ABCD"[r["answer"]])
            s_correct += int(ok); correct += int(ok); total += 1
        per_subject[subj] = s_correct / max(1, len(items))
        print(f"  {subj}: {s_correct}/{len(items)} = {per_subject[subj]:.3f}")

    score = correct / max(1, total)
    print(f"\nMMLU 5-shot accuracy = {score:.3f}  ({correct}/{total})")
    save_result(args.model, "mmlu", score,
                {"accuracy": score, "n_correct": correct, "n_total": total, "per_subject": per_subject},
                Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
