# ====================================================================================
# Deterministic, supplementary metrics (protocol 4.6). Not measures of clinical correctness.
# Usage:
#    - extract_falls_risk(summary: str) -> str
#    - rouge_l_f1(candidate: str, reference: str) -> float
# ====================================================================================

import re
from typing import List


def extract_falls_risk(summary: str) -> str:
    """
    Falls risk level (Low | Moderate | High) from section 5, or "Missing".
    """
    section = re.split(r"falls risk level", summary, flags=re.IGNORECASE)
    text = section[1] if len(section) > 1 else summary
    match = re.search(r"\b(low|moderate|high)\b", text, flags=re.IGNORECASE)
    return match.group(1).capitalize() if match else "Missing"


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def rouge_l_f1(candidate: str, reference: str) -> float:
    """
    ROUGE-L F1 on lowercased word tokens (longest common subsequence).
    """
    cand, ref = _tokens(candidate), _tokens(reference)
    if not cand or not ref:
        return 0.0

    # LCS with a single rolling row
    previous = [0] * (len(ref) + 1)
    for c in cand:
        current = [0]
        for j, r in enumerate(ref):
            current.append(previous[j] + 1 if c == r else max(previous[j + 1], current[j]))
        previous = current
    lcs = previous[-1]

    if lcs == 0:
        return 0.0
    precision, recall = lcs / len(cand), lcs / len(ref)
    return round(2 * precision * recall / (precision + recall), 4)
