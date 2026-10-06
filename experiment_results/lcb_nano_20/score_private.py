import os, sys, json, subprocess, types
sys.path.insert(0, "/home/ad/workspace/SYNKRASIS")
from data.LiveCodeBench.LiveCodeBench import LiveCodeBench
out = "experiment_results/lcb_nano_20"
ds = LiveCodeBench("x", output_dir="/tmp/claude-1000/scratch_ds")
done = {r["task_id"] for r in json.load(open(f"{out}/gpt-5-nano-2025-08-07_LiveCodeBench_results.json"))}
res = {}
for i in range(len(ds)):
    dp = ds.process(ds.data.iloc[i])
    if dp["task_id"] not in done: continue
    sol = f"services/Container/mount_dir/synk_lcb_local/task_{dp['task_id']}/solution.py"
    tests = json.loads(dp["private_test"]); fails = 0; first = ""
    for t in tests:
        try:
            p = subprocess.run([sys.executable, sol], input=t["input"], capture_output=True, text=True, timeout=10)
            if p.returncode: ok, why = False, "runtime_error"
            elif t["testtype"] == "functional":
                try: ok = json.loads(p.stdout.strip().splitlines()[-1]) == json.loads(t["output"])
                except Exception: ok = False
                why = "wrong_answer"
            else: ok, why = p.stdout.split() == t["output"].split(), "wrong_answer"
        except subprocess.TimeoutExpired: ok, why = False, "timeout"
        if not ok:
            fails += 1; first = first or why
    res[dp["task_id"]] = {"private_tests": len(tests), "failed": fails, "first_failure": first, "pass": fails == 0}
    print(dp["task_id"], res[dp["task_id"]], flush=True)
json.dump(res, open(f"{out}/private_test_rescore.json", "w"), indent=2)
print("private pass:", sum(v["pass"] for v in res.values()), "/", len(res))
