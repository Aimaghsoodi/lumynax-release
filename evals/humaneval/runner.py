"""HumanEval runner — pass@1 for code-generation models."""
import argparse, json, sys, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common.client import GatewayClient, save_result


PROMPT_TEMPLATE = """You are a Python coding assistant. Complete the following function. Return ONLY the function body — no explanation, no surrounding fences.

{prompt}
"""


def load_dataset(path: Path) -> list[dict]:
    # Expects HumanEval JSONL: {task_id, prompt, canonical_solution, test, entry_point}
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def extract_code(answer: str) -> str:
    m = re.search(r"```(?:python)?\n(.*?)```", answer, re.DOTALL)
    return (m.group(1) if m else answer).strip()


def check(item: dict, completion: str) -> bool:
    """Run the test against the completion in a subprocess (sandboxed by caller in prod)."""
    import subprocess, tempfile, textwrap
    code = textwrap.dedent(f"""
        {item['prompt']}
        {completion}
        {item['test']}
        check({item['entry_point']})
    """)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(code); path = f.name
    try:
        r = subprocess.run([sys.executable, path], capture_output=True, timeout=15)
        return r.returncode == 0
    except Exception:
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model",    required=True)
    p.add_argument("--gateway",  default="http://localhost:8080/v1")
    p.add_argument("--key",      default="lumynax-local-dev")
    p.add_argument("--dataset",  default="data/humaneval.jsonl",
                   help="Download from https://github.com/openai/human-eval (164 problems).")
    p.add_argument("--limit",    type=int, default=164)
    args = p.parse_args()

    ds_path = Path(args.dataset)
    if not ds_path.exists():
        print(f"dataset not found at {ds_path}.")
        print("download: curl -fsSL https://raw.githubusercontent.com/openai/human-eval/master/data/HumanEval.jsonl.gz | gunzip > data/humaneval.jsonl")
        sys.exit(2)
    items = load_dataset(ds_path)[: args.limit]

    client = GatewayClient(base_url=args.gateway, api_key=args.key)
    passed = 0
    sample_outputs = []
    for i, item in enumerate(items, 1):
        prompt = PROMPT_TEMPLATE.format(prompt=item["prompt"])
        out = client.chat(args.model, [{"role": "user", "content": prompt}],
                          temperature=0.0, max_tokens=512)
        code = extract_code(out)
        ok = check(item, code)
        passed += int(ok)
        if i <= 3:
            sample_outputs.append({"task_id": item["task_id"], "pass": ok, "completion": code[:300]})
        print(f"  [{i}/{len(items)}] {item['task_id']}: {'PASS' if ok else 'FAIL'}")

    score = passed / len(items)
    print(f"\nHumanEval pass@1 = {score:.3f}  ({passed}/{len(items)})")
    save_result(args.model, "humaneval", score,
                {"pass_at_1": score, "n_passed": passed, "n_total": len(items),
                 "samples": sample_outputs},
                Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
