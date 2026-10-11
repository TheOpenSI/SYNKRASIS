# Stage 2A.1 baseline benchmark

Same input + same prompt for every candidate model. Each output is compared with the OT-corrected reference summary by up to 2 LLM judges.

## Run

Edit the lists at the top of `main.py` in the repo root, then run it:

```python
MODELS = ["ollama:llama3.1:8b", "ollama:qwen2.5:14b"]       # any number, "backend:model"
JUDGES = ["ollama:gpt-oss:120b", "ollama:llama3.3:70b"]     # at most 2, keep constant
```

```bash
python main.py
```

`BenchmarkRunner` arguments: `models`, `judges`, `prompt_version` (default `0_3`), `judge_prompt_version` (`judge_0_1`), `case_ids` (default all 10), `run_name` (results folder; re-using one resumes the run, and adding a model to an existing run only generates and judges the new model), `num_ctx` (Ollama context window, default 16384; the prompt alone is ~7k tokens and the Ollama default would truncate it).

## Evaluation

Each judge scores 1-5 on the protocol 4.6 criteria: `coverage` (of reference content), `factual_consistency` (with the source), `unsupported_additions`, `clinical_safety` and `overall`. It also returns `aligned` (usable with at most minor edits) and a list of errors tagged with the 2A.1 taxonomy: omission, hallucination, terminology_drift, risk_interpretation, tone_register.

Judges are combined per case as follows:
- scores are the mean across judges
- `aligned` is a majority vote, and a tie counts as not aligned
- `needs_review` is set when the judges disagree on `aligned`, differ by 2 or more on `overall`, or one judge failed to return valid JSON. These cases go to human verification, because the LLM judge is not the sole basis for selection (protocol 4.3).

Deterministic supplementary metrics: falls-risk level match with the reference (parsed from section 5), ROUGE-L F1, word count, latency.

## Output: `Agents/results/<run_name>/`

| File | Content |
|---|---|
| `run_config.json` | models, judges, prompt versions, cases, settings, date |
| `generations/<model>/Case_<id>.txt / .json` | raw output (+ latency) |
| `judgements/<model>/Case_<id>__<judge>.json` | parsed verdict + raw judge response |
| `judge_scores.csv` | one row per model x case x judge |
| `case_results.csv` | one row per model x case, judges aggregated + metrics |
| `errors.csv` | every judge-reported error, for the error taxonomy |
| `summary.csv` | one row per model, ranked by aligned rate then overall score |

## Server notes

- `services/LLM/Ollama/Ollama.py` imports `torch` and pulls each model on first use.
- Only one model is loaded at a time: all cases are generated with each candidate in turn, then every generation is judged by judge 1, then by judge 2. Each Ollama model is unloaded (`keep_alive=0`) before the next is loaded, and every output is saved as soon as it is produced.
