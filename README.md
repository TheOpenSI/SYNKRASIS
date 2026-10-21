<div align="center">
 <img src="https://github.com/Adnan525/synkrasis/blob/master/SYNKRASIS.png" alt="SYNKRASIS" width="300"/>
</div>

# Synkrasis

An orchestrated suite of service-based applications designed for advanced Cognitive AI Systems. Synkrasis provides a seamless integration platform for AI-powered microservices.

## Prerequisites

Before you begin, ensure you have the following installed:

- [Docker](https://docs.docker.com/engine/install/ubuntu/) with appropriate user privileges for running Docker commands
- [Ollama](https://ollama.com/download) for local model serving
- Tested on Python 3.9.19

## Installation

1. Clone the repository:
  ```bash
  git clone https://github.com/yourusername/synkrasis.git
  cd synkrasis
  ```
2. Install required libraries:
 ```bash
 pip install -r requirements.txt
 ```

---

# Stage 2A.1: Baseline benchmark

The same input and prompt are given to each candidate model. Every output is compared with the OT-corrected reference summary by LLM judges.

## Run

Edit the lists at the top of `main.py`, then run `python main.py`.

```python
MODELS = ["ollama:a", "ollama:b", "ollama:c"]   # candidate models, "backend:model" (openai or ollama)
JUDGES = ["ollama:x", "ollama:y", "ollama:z"]   # judge models, any number
PROMPT_VERSION = "0_3"                          # prompts/prompt_0_3.txt
```

Only one model is loaded at a time. All cases are generated with `a`, then `b`, then `c` (each Ollama model is unloaded before the next). Then judge `x` judges every output, is unloaded, then judge `y` and so on. Everything is saved as it is produced, so a re-run with the same prompt skips what already exists. Results go to `Agents/results/prompt<version>/`, for example `prompt03` and `prompt04`.

```
Agents/results/prompt03/
  run_config.json                    models, judges, prompt versions, settings, date
  summary.csv                        one row per model
  <model>/generations/Case_<id>.txt  model output (also .json with latency)
  <model>/judgements/<judge>/Case_<id>.json   judge reasoning + parsed scores
  <model>/case_results.csv           one row per case, all judges combined
  <model>/summary.csv                one row, the model's stats
```

Ollama models need a context window larger than the default because the prompt is about 7k tokens. `BenchmarkRunner` sets `num_ctx=16384`.

## How judging works

Each judge gets the source optometry report, the OT-corrected reference summary and the candidate summary. It writes its reasoning and ends with a JSON object, which is parsed (a judge with no valid JSON is retried twice).

| Field | Meaning |
|---|---|
| coverage (1-5) | How much of the important content in the reference is in the candidate |
| factual_consistency (1-5) | Whether the candidate agrees with the source report and does not contradict the reference |
| hallucination (1-5) | 5 means nothing invented. Cautious "assess whether..." statements linked to a finding do not count as invented |
| aligned (yes/no) | Whether the candidate can replace the reference with at most minor edits |

Combining the judges for one case:
- `coverage`, `factual_consistency`, `hallucination` are the mean over the judges, and `overall` is the mean of those three.
- `aligned` is the majority vote: `yes`, `no`, or `tie` when the votes are equal. A tie is marked `human_review` = True. Use an odd number of judges to avoid ties.
- `judges_agreed` is True when every judge gave the same aligned answer.

Columns in `case_results.csv`: `yes_votes` is the number of judges that said aligned = yes out of `n_judges`.

Columns in `summary.csv`: `n_cases`, the mean of the four scores, `aligned_yes` / `aligned_no` / `aligned_tie` (number of cases per result), `judges_agreed` (number of cases where all judges agreed) and `human_review` (number of cases needing review).

Setup used below: candidate `gpt-5-nano-2025-08-07`, judges `gpt-5-mini-2025-08-07` and `gpt-5.4-mini-2026-03-17`, all 10 development cases, 1 generation per case. With 2 judges any 1-1 split is a tie, which is why many cases need review.

## Prompt v0.3 results (gpt-5-nano-2025-08-07 only)

| model | n_cases | coverage | factual_consistency | hallucination | overall | aligned_yes | aligned_no | aligned_tie | judges_agreed | human_review |
|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-nano-2025-08-07 | 10 | 4.45 | 4.1 | 3.9 | 4.15 | 5 | 0 | 5 | 5 | 5 |

Per case:

| case_id | coverage | factual_consistency | hallucination | overall | yes_votes | n_judges | aligned | judges_agreed | human_review |
|---|---|---|---|---|---|---|---|---|---|
| 032 | 4.5 | 3.5 | 3.0 | 3.67 | 1 | 2 | tie | False | True |
| 033 | 4.5 | 4.0 | 3.5 | 4.0 | 1 | 2 | tie | False | True |
| 035 | 4.5 | 4.5 | 4.5 | 4.5 | 2 | 2 | yes | True | False |
| 046 | 4.5 | 4.5 | 4.0 | 4.33 | 2 | 2 | yes | True | False |
| 057 | 4.0 | 4.5 | 4.0 | 4.17 | 1 | 2 | tie | False | True |
| 064 | 5.0 | 3.5 | 4.0 | 4.17 | 2 | 2 | yes | True | False |
| 066 | 4.5 | 4.5 | 4.5 | 4.5 | 2 | 2 | yes | True | False |
| 067 | 4.0 | 4.0 | 4.0 | 4.0 | 1 | 2 | tie | False | True |
| 072 | 4.5 | 4.5 | 4.0 | 4.33 | 2 | 2 | yes | True | False |
| 083 | 4.5 | 3.5 | 3.5 | 3.83 | 1 | 2 | tie | False | True |

## Prompt v0.4

v0.4 is v0.3 plus short generic additions (nothing removed), based on faults seen in the v0.3 outputs and on the differences between the Stage 1 drafts and the OT-corrected references. What it improves, with how often the pattern appears in the 10 outputs (v0.3 -> v0.4):

- **No rule labels as headings.** v0.3 copied its own rules ("A. ASSESS BEFORE PRESCRIBING", ..., "O. PRIORITISATION") into Section 4 in 10/10 outputs. v0.4 tells the model they are guidance, not headings: 10/10 -> 0/10.
- **Nothing after Section 6.** v0.3 added notes, a "Final checks" list or "If you'd like, I can..." in 10/10. v0.4 says to end after Section 6: 10/10 -> 4/10.
- **No raw measurements anywhere** (e.g. "6/30", "1.20 log units"), including Patient Context: 10/10 -> 1/10.
- **Low-vision referral only when it applies** (vision not correctable and affecting detail tasks) instead of by default: 10/10 -> 5/10.
- **Shorter, less repetitive output.** Each recommendation is stated once and driving is stated once, under Education and Support. Mean words 1419 -> 1147 (references: 696). Driving mentions only fell from 92 to 81.
- **Falls risk guide.** High for a confirmed fall linked to the vision impairment, Moderate for near-misses or stumbles, and a confirmed fall is not downgraded. This comes from the references and needs confirmation from the OT team.
- **Points the OTs added that v0.3 never produced** (present in the references): ability to call for help / personal alarm, flagging information the OT should clarify (for example why the person is not driving), mobility aids that identify the person as vision-impaired, and mobility routines presented as "O&M training may include...". These are added as rules in v0.4. They appear rarely so far (alarm 1/10, clarify 2/10, "training may include" 2/10, call for help 0/10, identified as vision-impaired 1/10).

| model | n_cases | coverage | factual_consistency | hallucination | overall | aligned_yes | aligned_no | aligned_tie | judges_agreed | human_review |
|---|---|---|---|---|---|---|---|---|---|---|
| gpt-5-nano-2025-08-07 | 10 | 4.25 | 4.25 | 3.95 | 4.15 | 2 | 1 | 7 | 3 | 7 |

Per case:

| case_id | coverage | factual_consistency | hallucination | overall | yes_votes | n_judges | aligned | judges_agreed | human_review |
|---|---|---|---|---|---|---|---|---|---|
| 032 | 3.5 | 3.5 | 3.0 | 3.33 | 0 | 2 | no | True | False |
| 033 | 4.5 | 4.0 | 4.0 | 4.17 | 1 | 2 | tie | False | True |
| 035 | 5.0 | 4.5 | 4.0 | 4.5 | 2 | 2 | yes | True | False |
| 046 | 4.5 | 4.5 | 4.5 | 4.5 | 1 | 2 | tie | False | True |
| 057 | 3.5 | 4.5 | 4.0 | 4.0 | 1 | 2 | tie | False | True |
| 064 | 4.5 | 4.0 | 3.5 | 4.0 | 1 | 2 | tie | False | True |
| 066 | 4.0 | 4.5 | 4.0 | 4.17 | 1 | 2 | tie | False | True |
| 067 | 4.0 | 4.5 | 4.5 | 4.33 | 1 | 2 | tie | False | True |
| 072 | 4.5 | 4.5 | 4.5 | 4.5 | 2 | 2 | yes | True | False |
| 083 | 4.5 | 4.0 | 3.5 | 4.0 | 1 | 2 | tie | False | True |

The judges do not show a gain for v0.4 on this model: `overall` is the same (4.15), and `coverage` went down (4.45 to 4.25), which is consistent with shorter outputs.
