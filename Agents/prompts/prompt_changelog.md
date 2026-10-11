# Prompt changelog

- `prompt_0_2.txt`: original synthetic-generation prompt; produced `data/before_correction/`.
- `prompt_0_3.txt`: revised by the OT team after the Stage 1 corrections (`data/02_OT_Reference_Summaries/`). Baseline used in `results/baseline_v03/`.
- `prompt_0_4.txt`: v0.3 plus minimal generic insertions addressing faults F1–F11. The faults were found in the Stage 1 draft vs reference diff and in the v0.3 baseline outputs. See `Agents/report.md` §3–4 for the evidence and the exact change for each fault. Not yet benchmarked.
- `judge_0_1.txt`: LLM-judge rubric (protocol §4.6 criteria + 2A.1 error taxonomy).
