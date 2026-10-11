# ====================================================================================
# Stage 2A data loader
# Loads optometry inputs, OT reference summaries and prompts from Agents/.
# Usage:
#    - list_case_ids() -> List[str]
#    - load_case(case_id: str) -> Dict[str, str]
#    - load_prompt(version: str) -> str
#    - load_text(path: str) -> str
# ====================================================================================

import os, sys

sys.path.append(f"{os.path.dirname(os.path.abspath(__file__))}/../..")

import re
from typing import Dict, List

AGENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INPUT_DIR = os.path.join(AGENTS_DIR, "data", "01_Optometry_Inputs")
REFERENCE_DIR = os.path.join(AGENTS_DIR, "data", "02_OT_Reference_Summaries")
PROMPT_DIR = os.path.join(AGENTS_DIR, "prompts")


def load_text(path: str) -> str:
    """
    Read a text file, dropping the BOM left by the docx conversion.
    """
    with open(path, "r", encoding="utf-8-sig") as file:
        return file.read().strip()


def list_case_ids() -> List[str]:
    """
    Case ids (e.g. "032") that have both an optometry input and an OT reference summary.
    """
    input_ids = {re.match(r"Case_(\d+)_", f).group(1) for f in os.listdir(INPUT_DIR)}
    reference_ids = {re.match(r"Case_(\d+)_", f).group(1) for f in os.listdir(REFERENCE_DIR)}
    return sorted(input_ids & reference_ids)


def load_case(case_id: str) -> Dict[str, str]:
    """
    Load one case as {"case_id", "input", "reference"}.
    """
    return {
        "case_id": case_id,
        "input": load_text(os.path.join(INPUT_DIR, f"Case_{case_id}_Optometry_Report.txt")),
        "reference": load_text(os.path.join(REFERENCE_DIR, f"Case_{case_id}_OT_Reference_Summary.txt")),
    }


def load_prompt(version: str) -> str:
    """
    Load a prompt by version, e.g. "0_4" -> prompts/prompt_0_4.txt, "judge_0_1" -> prompts/judge_0_1.txt.
    """
    file_name = f"{version}.txt" if version.startswith("judge") else f"prompt_{version}.txt"
    return load_text(os.path.join(PROMPT_DIR, file_name))
