import os, sys, json, subprocess, time, types
sys.path.insert(0, "/home/ad/workspace/SYNKRASIS")
for _m in ("scipy", "scipy.optimize"): sys.modules[_m] = types.ModuleType(_m)
sys.modules["scipy.optimize"].curve_fit = None
from data.LiveCodeBench.LiveCodeBench import LiveCodeBench
from utils.code_parsing.code_parser import parse_response
from services.PyCapsule.livecodebench_harness.LCBHarness import LCBHarness

S = os.path.dirname(__file__)
RUN = "experiment_results/lcb_nano_30"
H = LCBHarness()
results = json.load(open(f"{RUN}/gpt-5-nano-2025-08-07_LiveCodeBench_results.json"))
ds = LiveCodeBench("x", output_dir="/tmp/claude-1000/scratch_ds")
pts = {}
for i in range(len(ds)):
    dp = ds.process(ds.data.iloc[i]); pts[dp["task_id"]] = dp

def trace(code, dp, test, include_source):
    req = dict(code=code, mode=dp["test_type"], entry_point=dp["entry_point"], input=test["input"],
               expected=test["output"], include_source=include_source, max_steps=300000)
    t = time.time()
    try:
        p = subprocess.run([sys.executable, f"{S}/bpd_worker.py"], input=json.dumps(req), capture_output=True, text=True, timeout=90)
        out = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {"ok": False, "error": "no output: " + p.stderr[-300:]}
    except subprocess.TimeoutExpired:
        out = {"ok": False, "error": "timeout"}
    out["secs"] = round(time.time() - t, 1)
    return out

rows = []
for r in results:
    tid = r["task_id"]; dp = pts[tid]
    resp = open(f"{RUN}/responses/task_{tid}/attempt_0_response.txt").read()
    _, code = parse_response(resp)
    code = H.build_solution_content(dp, code).split("\n\nif __name__ == '__main__':")[0] if dp["test_type"] == "functional" else code
    tests = dp["public_test"]
    chosen, o = None, None
    for t in tests:                      # first public test the code gets wrong, else the first one
        o = trace(code, dp, t, False)
        if o.get("ok") and o["matches"] is False: chosen = t; break
    if chosen is None: chosen = tests[0]; o = trace(code, dp, tests[0], False)
    full = trace(code, dp, chosen, True)
    row = dict(task=tid, type=dp["test_type"], final=r["status"], attempt0_public_ok=(r["public_cleared_attempt"] == 0),
               ok=o.get("ok"), error=o.get("error"), matches=o.get("matches"), steps=o.get("steps"), secs=o.get("secs"),
               chars=len(o.get("report", "")), lines=o.get("report", "").count("\n"), chars_with_src=len(full.get("report", "")))
    rows.append(row); print(row, flush=True)
    if o.get("ok"):
        os.makedirs(f"{S}/traces", exist_ok=True)
        open(f"{S}/traces/{tid}.txt", "w").write(o["report"])
json.dump(rows, open(f"{S}/bpd_feasibility.json", "w"), indent=1)
