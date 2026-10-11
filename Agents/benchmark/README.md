# Stage 2A.1 baseline benchmark

Same input + same prompt for every candidate model. Each output is compared with the OT-corrected reference summary by up to 2 LLM judges.

## Run

From the repo root:

```bash
# quick test with the OpenAI defaults (generator gpt-5-nano, judges gpt-5-mini + gpt-5.4-mini)
python Agents/benchmark/run_benchmark.py --n_cases 2 --run_name smoke_test

# server, Ollama models (pass any number of candidate models, at most 2 judges)
python Agents/benchmark/run_benchmark.py --run_name ollama_v04 \
    --models ollama:llama3.1:8b ollama:qwen2.5:14b ollama:gemma2:27b \
    --judges ollama:gpt-oss:120b ollama:llama3.3:70b \
    --prompt 0_4 --num_ctx 16384
```

| Argument | Default | |
|---|---|---|
| `--models` | `openai:gpt-5-nano-2025-08-07` | `backend:model`, backend is `openai` or `ollama` |
| `--judges` | `openai:gpt-5-mini-2025-08-07 openai:gpt-5.4-mini-2026-03-17` | max 2, keep constant across runs |
| `--prompt` | `0_4` | `prompts/prompt_<version>.txt` (see `prompts/prompt_changelog.md`) |
| `--judge_prompt` | `judge_0_1` | `prompts/judge_0_1.txt` |
| `--cases` / `--n_cases` | all 10 | subset of case ids / first n |
| `--num_ctx` | 16384 | Ollama context window; the prompt alone is ~7k tokens, the Ollama default would truncate it |
| `--run_name` | timestamp | re-using a name resumes, existing generations/judgements are not regenerated |

To add a model to an existing run, re-run with the same `--run_name` and the extra model; only the new model is generated and judged.

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
| `run_config.json` | models, judges, prompt versions + sha256, settings, git commit, date, host |
| `generations/<model>/Case_<id>.txt / .json` | raw output (+ latency, timestamp) |
| `judgements/<model>/Case_<id>__<judge>.json` | parsed verdict + raw judge response |
| `judge_scores.csv` | one row per model x case x judge |
| `case_results.csv` | one row per model x case, judges aggregated + metrics |
| `errors.csv` | every judge-reported error, for the error taxonomy |
| `summary.csv` | one row per model, ranked by aligned rate then overall score |

## Server notes

- `services/LLM/Ollama/Ollama.py` imports `torch` and pulls each model on first use.
- Candidate models are generated first and judges run afterwards, so a large local judge does not compete with the candidates for VRAM.
