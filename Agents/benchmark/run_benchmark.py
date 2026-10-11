# ====================================================================================
# Stage 2A.1 baseline benchmark.
# Generates an OT summary per case for each candidate model, judges each summary against
# the OT reference summary with up to 2 judge models, and saves everything under
# Agents/results/<run_name>/. Re-running with the same run_name resumes (existing files are reused).
#
# Usage (from repo root):
#    python Agents/benchmark/run_benchmark.py --n_cases 2
#    python Agents/benchmark/run_benchmark.py --run_name ollama_v04 \
#        --models ollama:llama3.1:8b ollama:qwen2.5:14b \
#        --judges ollama:gpt-oss:120b ollama:llama3.3:70b
# ====================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import argparse, hashlib, json, platform, subprocess, time
from datetime import datetime
from typing import Dict, List

import pandas as pd

from Agents.benchmark.data_loader import AGENTS_DIR, list_case_ids, load_case, load_prompt
from Agents.benchmark.judge import Judge, aggregate_verdicts, SCORE_KEYS
from Agents.benchmark.llm_factory import build_llm, safe_name
from Agents.benchmark.metrics import extract_falls_risk, rouge_l_f1
from utils.output_message_format.output_colour import print_info, print_success

DEFAULT_MODELS = ["openai:gpt-5-nano-2025-08-07"]
DEFAULT_JUDGES = ["openai:gpt-5-mini-2025-08-07", "openai:gpt-5.4-mini-2026-03-17"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 2A.1 baseline benchmark")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS,
                        help="candidate models as backend:model, e.g. openai:gpt-5-nano-2025-08-07 ollama:llama3.1:8b")
    parser.add_argument("--judges", nargs="+", default=DEFAULT_JUDGES, help="at most 2 judge models")
    parser.add_argument("--prompt", default="0_4", help="generation prompt version, prompts/prompt_<version>.txt")
    parser.add_argument("--judge_prompt", default="judge_0_1", help="judge prompt, prompts/<name>.txt")
    parser.add_argument("--cases", nargs="+", default=None, help="case ids, e.g. 032 046. Defaults to all")
    parser.add_argument("--n_cases", type=int, default=None, help="use only the first n cases")
    parser.add_argument("--num_ctx", type=int, default=16384, help="Ollama context window")
    parser.add_argument("--run_name", default=None, help="results folder name, defaults to a timestamp")
    args = parser.parse_args()

    if len(args.judges) > 2:
        parser.error("At most 2 judges are supported")
    return args


def read_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: str, data: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def save_run_config(args: argparse.Namespace, run_dir: str, case_ids: List[str], prompt: str, judge_prompt: str) -> None:
    """
    Record everything needed to reproduce the run (protocol section 5).
    """
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = ""
    write_json(os.path.join(run_dir, "run_config.json"), {
        "date": datetime.now().isoformat(timespec="seconds"),
        "models": args.models,
        "judges": args.judges,
        "prompt_version": args.prompt,
        "prompt_sha256": sha256(prompt),
        "judge_prompt_version": args.judge_prompt,
        "judge_prompt_sha256": sha256(judge_prompt),
        "case_ids": case_ids,
        "generation_settings": {"openai": "temperature=1 (model default), seed=42",
                                "ollama": {"num_ctx": args.num_ctx, "seed": 42}},
        "generations_per_case": 1,
        "aggregation": "mean scores; majority vote on aligned (tie = not aligned); "
                       "needs_review if judges disagree, overall spread >= 2 or a judge failed",
        "git_commit": commit,
        "python": platform.python_version(),
        "host": platform.node(),
    })


def generate(model_spec: str, prompt: str, cases: List[Dict], run_dir: str, num_ctx: int) -> Dict[str, Dict]:
    """
    Generate (or reload) one summary per case for a candidate model.
    """
    out_dir = os.path.join(run_dir, "generations", safe_name(model_spec))
    generations, llm = {}, None
    for case in cases:
        path = os.path.join(out_dir, f"Case_{case['case_id']}.json")
        if os.path.exists(path):
            generations[case["case_id"]] = read_json(path)
            continue

        llm = llm or build_llm(model_spec, prompt, num_ctx)
        print_info(f"Generating case {case['case_id']} with {model_spec}")
        start = time.time()
        summary = (llm.generate_response(case["input"]) or "").strip()
        record = {"model": model_spec, "case_id": case["case_id"], "summary": summary,
                  "latency_s": round(time.time() - start, 2),
                  "timestamp": datetime.now().isoformat(timespec="seconds")}
        write_json(path, record)
        with open(path.replace(".json", ".txt"), "w", encoding="utf-8") as file:
            file.write(summary)
        generations[case["case_id"]] = record
    return generations


def judge_case(judges: List[Judge], model_spec: str, case: Dict, summary: str, run_dir: str) -> List[Dict]:
    """
    Judge (or reload) one candidate summary with every judge.
    """
    out_dir = os.path.join(run_dir, "judgements", safe_name(model_spec))
    verdicts = []
    for judge in judges:
        path = os.path.join(out_dir, f"Case_{case['case_id']}__{safe_name(judge.model_spec)}.json")
        if os.path.exists(path):
            verdicts.append(read_json(path))
            continue
        print_info(f"Judging case {case['case_id']} of {model_spec} with {judge.model_spec}")
        verdict = judge.evaluate(case, summary)
        write_json(path, verdict)
        verdicts.append(verdict)
    return verdicts


def save_tables(run_dir: str, judge_rows: List[Dict], case_rows: List[Dict], error_rows: List[Dict]) -> pd.DataFrame:
    """
    Save the per-judge, per-case and per-model tables as CSV. Returns the per-model summary.
    """
    pd.DataFrame(judge_rows).to_csv(os.path.join(run_dir, "judge_scores.csv"), index=False)
    pd.DataFrame(error_rows, columns=["model", "case_id", "judge", "category", "severity", "description"]) \
        .to_csv(os.path.join(run_dir, "errors.csv"), index=False)

    case_df = pd.DataFrame(case_rows)
    case_df.to_csv(os.path.join(run_dir, "case_results.csv"), index=False)

    summary_df = case_df.groupby("model").agg(
        n_cases=("case_id", "count"),
        **{key: (key, "mean") for key in SCORE_KEYS},
        aligned_rate=("aligned", "mean"),
        falls_risk_accuracy=("falls_risk_match", "mean"),
        rouge_l_f1=("rouge_l_f1", "mean"),
        needs_review=("needs_review", "sum"),
        words=("words", "mean"),
        latency_s=("latency_s", "mean"),
    ).round(3).sort_values(["aligned_rate", "overall"], ascending=False)
    summary_df.to_csv(os.path.join(run_dir, "summary.csv"))
    return summary_df


def main() -> None:
    args = parse_args()
    run_name = args.run_name or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(AGENTS_DIR, "results", run_name)

    case_ids = args.cases or list_case_ids()
    case_ids = case_ids[:args.n_cases] if args.n_cases else case_ids
    cases = [load_case(case_id) for case_id in case_ids]
    prompt = load_prompt(args.prompt)
    judge_prompt = load_prompt(args.judge_prompt)
    save_run_config(args, run_dir, case_ids, prompt, judge_prompt)

    # Generate first, so local models are not competing with judge models for memory
    all_generations = {model: generate(model, prompt, cases, run_dir, args.num_ctx) for model in args.models}

    judges = [Judge(judge_spec, judge_prompt) for judge_spec in args.judges]
    judge_rows, case_rows, error_rows = [], [], []
    for model, generations in all_generations.items():
        for case in cases:
            record = generations[case["case_id"]]
            verdicts = judge_case(judges, model, case, record["summary"], run_dir)

            for verdict in verdicts:
                judge_rows.append({"model": model, "case_id": case["case_id"],
                                   **{k: v for k, v in verdict.items() if k not in ("errors", "raw_response")}})
                for error in verdict.get("errors", []):
                    error_rows.append({"model": model, "case_id": case["case_id"], "judge": verdict["judge"], **error})

            falls_risk = extract_falls_risk(record["summary"])
            reference_falls_risk = extract_falls_risk(case["reference"])
            case_rows.append({"model": model, "case_id": case["case_id"],
                              **aggregate_verdicts(verdicts),
                              "falls_risk": falls_risk,
                              "reference_falls_risk": reference_falls_risk,
                              "falls_risk_match": falls_risk == reference_falls_risk,
                              "rouge_l_f1": rouge_l_f1(record["summary"], case["reference"]),
                              "words": len(record["summary"].split()),
                              "latency_s": record["latency_s"]})

    summary_df = save_tables(run_dir, judge_rows, case_rows, error_rows)
    print_success(f"Results saved to {run_dir}")
    print(summary_df.to_string())


if __name__ == "__main__":
    main()
