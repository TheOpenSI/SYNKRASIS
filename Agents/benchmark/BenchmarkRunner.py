# ====================================================================================
# Stage 2A.1 baseline benchmark runner.
# Runs in 3 phases so only one model is loaded at a time (small GPU):
#    1. generate all cases with model a, unload, then model b, ...
#    2. judge all generations with judge x, unload, then judge y
#    3. aggregate the saved judgements into tables
# Everything is saved to Agents/results/<run_name>/ as it is produced; re-running with the
# same run_name reuses existing files.
# Usage:
#    - BenchmarkRunner(models, judges, prompt_version="0_3").run() -> pd.DataFrame
# ====================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json, time
from datetime import datetime
from typing import Dict, List

import pandas as pd

from Agents.benchmark.data_loader import AGENTS_DIR, list_case_ids, load_case, load_prompt
from Agents.benchmark.judge import Judge, aggregate_verdicts, SCORE_KEYS
from Agents.benchmark.llm_factory import build_llm, safe_name
from Agents.benchmark.metrics import extract_falls_risk, rouge_l_f1
from utils.output_message_format.output_colour import print_info, print_success


def read_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: str, data: Dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


class BenchmarkRunner:
    def __init__(self,
                 models: List[str],
                 judges: List[str],
                 prompt_version: str = "0_3",
                 judge_prompt_version: str = "judge_0_1",
                 case_ids: List[str] = None,
                 run_name: str = None,
                 num_ctx: int = 16384):
        """
        Args:
            models (List[str]): candidate models as "backend:model", e.g. "ollama:llama3.1:8b"
            judges (List[str]): at most 2 judge models, keep constant across runs
            prompt_version (str): prompts/prompt_<version>.txt
            judge_prompt_version (str): prompts/<version>.txt
            case_ids (List[str], optional): subset of cases, defaults to all
            run_name (str, optional): results folder name, defaults to a timestamp
            num_ctx (int): Ollama context window, the prompt alone is ~7k tokens
        """
        if len(judges) > 2:
            raise ValueError("At most 2 judges are supported")
        self.models = models
        self.judges = judges
        self.prompt_version = prompt_version
        self.judge_prompt_version = judge_prompt_version
        self.num_ctx = num_ctx
        self.cases = [load_case(case_id) for case_id in (case_ids or list_case_ids())]
        self.prompt = load_prompt(prompt_version)
        self.judge_prompt = load_prompt(judge_prompt_version)
        self.run_dir = os.path.join(AGENTS_DIR, "results",
                                    run_name or datetime.now().strftime("%Y%m%d_%H%M%S"))


    def _save_config(self) -> None:
        """
        Record what is needed to reproduce the run (protocol section 5).
        """
        write_json(os.path.join(self.run_dir, "run_config.json"), {
            "date": datetime.now().isoformat(timespec="seconds"),
            "models": self.models,
            "judges": self.judges,
            "prompt_version": self.prompt_version,
            "judge_prompt_version": self.judge_prompt_version,
            "case_ids": [case["case_id"] for case in self.cases],
            "ollama_options": {"num_ctx": self.num_ctx, "seed": 42},
            "openai_settings": "temperature=1 (model default), seed=42",
            "generations_per_case": 1,
            "aggregation": "mean scores; majority vote on aligned (tie = not aligned); "
                           "needs_review if judges disagree, overall spread >= 2 or a judge failed",
        })


    def _generate(self, model: str) -> Dict[str, Dict]:
        """
        Generate (or reload) one summary per case for a candidate model.
        """
        out_dir = os.path.join(self.run_dir, "generations", safe_name(model))
        generations, llm = {}, None
        for case in self.cases:
            path = os.path.join(out_dir, f"Case_{case['case_id']}.json")
            if os.path.exists(path):
                generations[case["case_id"]] = read_json(path)
                continue

            llm = llm or build_llm(model, self.prompt, self.num_ctx)
            print_info(f"Generating case {case['case_id']} with {model}")
            start = time.time()
            summary = (llm.generate_response(case["input"]) or "").strip()
            record = {"model": model, "case_id": case["case_id"], "summary": summary,
                      "latency_s": round(time.time() - start, 2)}
            write_json(path, record)
            with open(path.replace(".json", ".txt"), "w", encoding="utf-8") as file:
                file.write(summary)
            generations[case["case_id"]] = record

        if llm:
            llm.cleanup() # unload before the next model
        return generations


    def _judgement_path(self, model: str, case_id: str, judge: str) -> str:
        return os.path.join(self.run_dir, "judgements", safe_name(model),
                            f"Case_{case_id}__{safe_name(judge)}.json")


    def _judge(self, judge_spec: str, generations: Dict[str, Dict[str, Dict]]) -> None:
        """
        Judge (or skip if already saved) every generation of every model with one judge, then unload it.
        """
        judge = None
        for model in self.models:
            for case in self.cases:
                path = self._judgement_path(model, case["case_id"], judge_spec)
                if os.path.exists(path):
                    continue
                judge = judge or Judge(judge_spec, self.judge_prompt)
                print_info(f"Judging case {case['case_id']} of {model} with {judge_spec}")
                write_json(path, judge.evaluate(case, generations[model][case["case_id"]]["summary"]))

        if judge:
            judge.cleanup() # unload before the next judge


    def _save_tables(self, judge_rows: List[Dict], case_rows: List[Dict], error_rows: List[Dict]) -> pd.DataFrame:
        """
        Save per-judge, per-case, error and per-model tables as CSV. Returns the per-model summary.
        """
        pd.DataFrame(judge_rows).to_csv(os.path.join(self.run_dir, "judge_scores.csv"), index=False)
        pd.DataFrame(error_rows, columns=["model", "case_id", "judge", "category", "severity", "description"]) \
            .to_csv(os.path.join(self.run_dir, "errors.csv"), index=False)

        case_df = pd.DataFrame(case_rows)
        case_df.to_csv(os.path.join(self.run_dir, "case_results.csv"), index=False)

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
        summary_df.to_csv(os.path.join(self.run_dir, "summary.csv"))
        return summary_df


    def run(self) -> pd.DataFrame:
        """
        Generate with each model, then judge with each judge, one model loaded at a time. Then aggregate.
        """
        self._save_config()

        # Phase 1: generation, one candidate model at a time
        generations = {model: self._generate(model) for model in self.models}

        # Phase 2: judgement, one judge model at a time
        for judge_spec in self.judges:
            self._judge(judge_spec, generations)

        # Phase 3: aggregate the saved judgements
        judge_rows, case_rows, error_rows = [], [], []
        for model in self.models:
            for case in self.cases:
                record = generations[model][case["case_id"]]
                verdicts = [read_json(self._judgement_path(model, case["case_id"], judge_spec))
                            for judge_spec in self.judges]

                for verdict in verdicts:
                    judge_rows.append({"model": model, "case_id": case["case_id"],
                                       **{k: v for k, v in verdict.items() if k not in ("errors", "raw_response")}})
                    for error in verdict.get("errors", []):
                        error_rows.append({"model": model, "case_id": case["case_id"],
                                           "judge": verdict["judge"], **error})

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

        summary_df = self._save_tables(judge_rows, case_rows, error_rows)
        print_success(f"Results saved to {self.run_dir}")
        return summary_df


    def cleanup(self):
        print_success("BenchmarkRunner has nothing to clean up.")
