# ====================================================================================
# LLM-as-judge for candidate OT summaries against the OT reference summaries.
# The judge writes its reasoning, then ends with a JSON object that is parsed here.
# Usage:
#    - Judge(model_spec: str, judge_prompt: str).evaluate(case: Dict, candidate: str) -> Dict
#    - Judge.cleanup()
#    - aggregate_verdicts(verdicts: List[Dict]) -> Dict
# ====================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json, re
from typing import Dict, List, Optional

from Agents.benchmark.llm_factory import build_llm
from utils.output_message_format.output_colour import print_warning

SCORE_KEYS = ["coverage", "factual_consistency", "hallucination"]


class Judge:
    def __init__(self,
                 model_spec: str,
                 judge_prompt: str,
                 max_retries: int = 2):
        """
        One judge model.

        Args:
            model_spec (str): "openai:<model>" or "ollama:<model>"
            judge_prompt (str): system prompt with the criteria and the JSON output format
            max_retries (int): extra attempts when the response has no valid JSON
        """
        self.model_spec = model_spec
        self.max_retries = max_retries
        self.llm = build_llm(model_spec, judge_prompt)


    def _build_user_prompt(self, case: Dict, candidate: str) -> str:
        return (f"SOURCE:\n{case['input']}\n\n"
                f"REFERENCE:\n{case['reference']}\n\n"
                f"CANDIDATE:\n{candidate}")


    def _parse(self, response: str) -> Optional[Dict]:
        """
        Parse the last JSON object in the response (the reasoning comes before it).
        """
        matches = re.findall(r"\{[^{}]*\}", response)
        if not matches:
            return None
        try:
            verdict = json.loads(matches[-1])
            result = {key: int(verdict[key]) for key in SCORE_KEYS}
            result["aligned"] = str(verdict["aligned"]).strip().lower()
        except (ValueError, KeyError, TypeError):
            return None

        if result["aligned"] not in ("yes", "no") or not all(1 <= result[key] <= 5 for key in SCORE_KEYS):
            return None
        return result


    def evaluate(self, case: Dict, candidate: str) -> Dict:
        """
        Judge one candidate summary. Returns the parsed verdict plus the full raw response.
        """
        user_prompt = self._build_user_prompt(case, candidate)
        response = ""
        for attempt in range(self.max_retries + 1):
            response = self.llm.generate_response(user_prompt) or ""
            verdict = self._parse(response)
            if verdict:
                return {"judge": self.model_spec, "valid": True, **verdict, "raw_response": response}
            print_warning(f"{self.model_spec} returned no valid JSON (attempt {attempt + 1})")
        return {"judge": self.model_spec, "valid": False, "raw_response": response}


    def cleanup(self):
        """
        Release the judge model (unloads it from VRAM for Ollama).
        """
        self.llm.cleanup()


def aggregate_verdicts(verdicts: List[Dict]) -> Dict:
    """
    Combine the judges for one case.
    Scores are the mean over judges and overall is the mean of the three scores.
    aligned is the majority vote (yes | no), a tie is "tie" and needs human review.

    Returns:
        Dict: coverage, factual_consistency, hallucination, overall, yes_votes, n_judges,
              aligned, judges_agreed, human_review
    """
    valid = [v for v in verdicts if v["valid"]]
    if not valid:
        return {"n_judges": 0, "aligned": "tie", "judges_agreed": False, "human_review": True}

    result = {key: round(sum(v[key] for v in valid) / len(valid), 2) for key in SCORE_KEYS}
    result["overall"] = round(sum(result[key] for key in SCORE_KEYS) / len(SCORE_KEYS), 2)

    yes_votes = sum(v["aligned"] == "yes" for v in valid)
    no_votes = len(valid) - yes_votes
    result["yes_votes"] = yes_votes
    result["n_judges"] = len(valid)
    result["aligned"] = "yes" if yes_votes > no_votes else "no" if no_votes > yes_votes else "tie"
    result["judges_agreed"] = yes_votes == 0 or no_votes == 0
    result["human_review"] = result["aligned"] == "tie"
    return result
