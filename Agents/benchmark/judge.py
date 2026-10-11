# ====================================================================================
# LLM-as-judge for candidate OT summaries against the OT reference summaries.
# Usage:
#    - Judge(model_spec: str, judge_prompt: str).evaluate(case: Dict, candidate: str) -> Dict
#    - aggregate_verdicts(verdicts: List[Dict]) -> Dict
# ====================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import json
from typing import Dict, List, Optional

from Agents.benchmark.llm_factory import build_llm
from utils.output_message_format.output_colour import print_warning

SCORE_KEYS = ["coverage", "factual_consistency", "unsupported_additions", "clinical_safety", "overall"]


class Judge:
    def __init__(self,
                 model_spec: str,
                 judge_prompt: str,
                 max_retries: int = 2):
        """
        One judge model.

        Args:
            model_spec (str): "openai:<model>" or "ollama:<model>"
            judge_prompt (str): system prompt with the rubric and JSON output format
            max_retries (int): extra attempts when the response is not valid JSON
        """
        self.model_spec = model_spec
        self.max_retries = max_retries
        self.llm = build_llm(model_spec, judge_prompt)


    def _build_user_prompt(self, case: Dict, candidate: str) -> str:
        return (f"SOURCE OPTOMETRY REPORT:\n{case['input']}\n\n"
                f"REFERENCE OT SUMMARY:\n{case['reference']}\n\n"
                f"CANDIDATE OT SUMMARY:\n{candidate}")


    def _parse(self, response: str) -> Optional[Dict]:
        """
        Parse the JSON object from the response, tolerating code fences or surrounding text.
        """
        try:
            verdict = json.loads(response[response.index("{"): response.rindex("}") + 1])
            for key in SCORE_KEYS:
                verdict[key] = int(verdict[key])
            verdict["aligned"] = bool(verdict["aligned"])
            verdict.setdefault("errors", [])
            return verdict
        except (ValueError, KeyError, TypeError):
            return None


    def evaluate(self, case: Dict, candidate: str) -> Dict:
        """
        Judge one candidate summary. Returns the parsed verdict plus the raw response.
        """
        user_prompt = self._build_user_prompt(case, candidate)
        response = ""
        for attempt in range(self.max_retries + 1):
            response = self.llm.generate_response(user_prompt) or ""
            verdict = self._parse(response)
            if verdict:
                return {"judge": self.model_spec, "valid": True, **verdict, "raw_response": response}
            print_warning(f"{self.model_spec} returned invalid JSON (attempt {attempt + 1})")
        return {"judge": self.model_spec, "valid": False, "raw_response": response}


def aggregate_verdicts(verdicts: List[Dict]) -> Dict:
    """
    Combine judges: mean scores, majority vote on "aligned" (ties count as not aligned),
    and flag for human review when judges disagree on "aligned" or differ by 2+ on "overall".
    """
    valid = [v for v in verdicts if v["valid"]]
    if not valid:
        return {"n_judges": 0, "aligned": False, "needs_review": True}

    result = {key: round(sum(v[key] for v in valid) / len(valid), 2) for key in SCORE_KEYS}
    votes = sum(v["aligned"] for v in valid)
    overall_scores = [v["overall"] for v in valid]

    result["n_judges"] = len(valid)
    result["aligned_votes"] = votes
    result["aligned"] = votes > len(valid) / 2
    result["judges_agree"] = votes in (0, len(valid))
    result["overall_spread"] = max(overall_scores) - min(overall_scores)
    result["needs_review"] = (not result["judges_agree"]
                              or result["overall_spread"] >= 2
                              or len(valid) < len(verdicts))
    return result
