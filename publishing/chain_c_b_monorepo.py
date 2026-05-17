"""After Pack A completes, run Pack C, then Pack B, then refresh GitHub monorepo."""
import sys, subprocess, time
sys.path.insert(0, r"S:\hf-publish")

def run(label, mod):
    print(f"\n\n>>>>>>> {label} START at {time.strftime('%Y-%m-%d %H:%M:%S')} >>>>>>>", flush=True)
    try:
        m = __import__(mod)
        m.main()
        print(f">>>>>>> {label} OK at {time.strftime('%Y-%m-%d %H:%M:%S')} >>>>>>>", flush=True)
    except Exception as e:
        print(f">>>>>>> {label} FAIL: {e} >>>>>>>", flush=True)

run("Pack C — Document & Retrieval", "pack_c_ship")
run("Pack B — Frontier Round 2",      "pack_b_ship")

# Refresh GitHub monorepo
print(f"\n>>>>>>> GitHub monorepo refresh START at {time.strftime('%Y-%m-%d %H:%M:%S')} >>>>>>>", flush=True)
try:
    subprocess.run(["py", "-3", r"S:\hf-publish\build_github_monorepo.py"], check=True)
    import os
    cwd = r"C:\Users\ijadimaa\AppData\Local\Temp\aimaghsoodi-mirror\lumynax-release"
    subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)
    subprocess.run(["git", "-c", "core.autocrlf=false", "commit", "-m",
                    f"chore: add Packs A/C/B — speech + doc + frontier-round-2 ({time.strftime('%Y-%m-%d')})"],
                   cwd=cwd, check=False)
    subprocess.run(["git", "push", "origin", "main"], cwd=cwd, check=True)
    print(">>>>>>> GitHub monorepo refresh OK >>>>>>>", flush=True)
except Exception as e:
    print(f">>>>>>> GitHub monorepo refresh FAIL: {e} >>>>>>>", flush=True)
