# ====================================================================================
# Stage 2A.1 baseline benchmark runner.
# Runs in 3 phases so only one model is loaded at a time (small GPU):
#    1. generate all cases with model a, unload, then model b, ...
#    2. judge all generations with judge x, unload, then judge y, ...
#    3. consolidate the saved judgements into tables
# Layout (everything is saved as it is produced, re-running skips what already exists):
#    Agents/results/<run_name>/
#        run_config.json
#        summary.csv                          one row per model
#        <model>/generations/Case_<id>.txt|.json
#        <model>/judgements/<judge>/Case_<id>.json
#        <model>/case_results.csv             one row per case
#        <model>/summary.csv                  one row, the model's stats
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
                 judge_prompt_version: str = "judge_0_2",
                 case_ids: List[str] = None,
                 run_name: str = None,
                 num_ctx: int = 16384):
        """
        Args:
            models (List[str]): candidate models as "backend:model", e.g. "ollama:llama3.1:8b"
            judges (List[str]): judge models, any number. An even number can tie (needs human review)
            prompt_version (str): prompts/prompt_<version>.txt
            judge_prompt_version (str): prompts/<version>.txt
            case_ids (List[str], optional): subset of cases, defaults to all
            run_name (str, optional): results folder name, defaults to "prompt03" for prompt 0_3
            num_ctx (int): Ollama context window, the prompt alone is ~7k tokens
        """
        if not judges:
            raise ValueError("At least 1 judge is needed")
        self.models = models
        self.judges = judges
        self.prompt_version = prompt_version
        self.judge_prompt_version = judge_prompt_version
        self.num_ctx = num_ctx
        self.cases = [load_case(case_id) for case_id in (case_ids or list_case_ids())]
        self.prompt = load_prompt(prompt_version)
        self.judge_prompt = load_prompt(judge_prompt_version)
        self.run_dir = os.path.join(AGENTS_DIR, "results", run_name or f"prompt{prompt_version.replace('_', '')}")


    def _model_dir(self, model: str) -> str:
        return os.path.join(self.run_dir, safe_name(model))


    def _judgement_path(self, model: str, case_id: str, judge: str) -> str:
        return os.path.join(self._model_dir(model), "judgements", safe_name(judge), f"Case_{case_id}.json")


    def _save_config(self) -> None:
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
        })


    def _generate(self, model: str) -> Dict[str, Dict]:
        """
        Generate (or reload) one summary per case for a candidate model, then unload it.
        """
        out_dir = os.path.join(self._model_dir(model), "generations")
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


    def _consolidate(self, model: str) -> Dict:
        """
        Combine the saved judgements of one model into case_results.csv and a one row summary.csv.
        """
        rows = []
        for case in self.cases:
            verdicts = [read_json(self._judgement_path(model, case["case_id"], judge)) for judge in self.judges]
            rows.append({"case_id": case["case_id"], **aggregate_verdicts(verdicts)})
        case_df = pd.DataFrame(rows)
        case_df.to_csv(os.path.join(self._model_dir(model), "case_results.csv"), index=False)

        summary = {"model": model, "n_cases": len(case_df),
                   **{key: round(case_df[key].mean(), 2) for key in SCORE_KEYS + ["overall"]},
                   "aligned_yes": int((case_df["aligned"] == "yes").sum()),
                   "aligned_no": int((case_df["aligned"] == "no").sum()),
                   "aligned_tie": int((case_df["aligned"] == "tie").sum()),
                   "judges_agreed": int(case_df["judges_agreed"].sum()),
                   "human_review": int(case_df["human_review"].sum())}
        pd.DataFrame([summary]).to_csv(os.path.join(self._model_dir(model), "summary.csv"), index=False)
        return summary


    def run(self) -> pd.DataFrame:
        """
        Generate with each model, judge with each judge (one model loaded at a time), then consolidate.
        """
        self._save_config()

        generations = {model: self._generate(model) for model in self.models}
        for judge_spec in self.judges:
            self._judge(judge_spec, generations)

        summary_df = pd.DataFrame([self._consolidate(model) for model in self.models])
        summary_df.to_csv(os.path.join(self.run_dir, "summary.csv"), index=False)
        print_success(f"Results saved to {self.run_dir}")
        return summary_df


    def cleanup(self):
        print_success("BenchmarkRunner has nothing to clean up.")
