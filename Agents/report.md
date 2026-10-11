# Stage 2A.1 — Work Report

## 1. What was changed

### 1.1 Data
- All `.docx` files under `Agents/` were converted to UTF-8 `.txt`

### 1.2 Code
| File | Change |
|---|---|
| `main.py` | Rewritten as the benchmark entry point. The `MODELS` (candidates) and `JUDGES` (max 2) lists are at the top; it runs `BenchmarkRunner`. The old chat loop imported modules that no longer exist on this branch (`services.Container`, `utils.resource`). |
| `Agents/benchmark/BenchmarkRunner.py` | Runner class: generate → judge → save. Resumable: re-running with the same `run_name` reuses existing outputs. |
| `Agents/benchmark/judge.py` | `Judge` class (robust JSON parsing with retries) and `aggregate_verdicts()` |
| `Agents/benchmark/llm_factory.py` | `"openai:<model>"` / `"ollama:<model>"` → existing `OpenAI_GPT` / `Ollama` services |
| `Agents/benchmark/data_loader.py` | Loads cases, references and prompts |
| `Agents/benchmark/metrics.py` | Deterministic checks: falls-risk level parser and ROUGE-L F1 |
| `Agents/prompts/judge_0_1.txt` | Judge rubric (protocol §4.6 criteria + 2A.1 error taxonomy) |
| `services/LLM/Ollama/Ollama.py` | Optional `options` passed to `ollama.generate` (+4/−2 lines). Without it, Ollama's 2–4k default context silently truncates the ~7k-token prompt. Existing callers are unchanged. |

`OpenAI_GPT` was tested with gpt-5-nano, gpt-5-mini and gpt-5.4-mini.

### 1.3 How judging works
- Each judge sees the **source report, the reference and the candidate**. It scores 1–5 on `coverage`, `factual_consistency`, `unsupported_additions`, `clinical_safety` and `overall`.
- It also returns `aligned` (usable with at most minor edits) and a list of errors tagged omission, hallucination, terminology_drift, risk_interpretation or tone_register, each marked major or minor.
- **Combining the 2 judges:**
  - scores are averaged
  - `aligned` is a majority vote, and a 1–1 tie counts as **not aligned**
  - `needs_review` is set when the judges disagree on `aligned`, differ by 2 or more on `overall`, or a judge fails. These cases go to manual verification (protocol §4.3).
- **Judge-independent checks:** the falls-risk level must exactly match the reference, and ROUGE-L is reported as a supplementary metric.

### 1.4 Saved data: `Agents/results/<run_name>/`
`run_config.json`, `generations/<model>/Case_<id>.txt|.json`, `judgements/<model>/Case_<id>__<judge>.json` (including the raw judge response), `judge_scores.csv`, `case_results.csv`, `errors.csv`, `summary.csv`.

---

## 2. v0.3 baseline results (`results/baseline_v03/`)

Generator `gpt-5-nano-2025-08-07`, judges `gpt-5-mini-2025-08-07` + `gpt-5.4-mini-2026-03-17`, all 10 development cases, 1 generation per case.

| coverage | factual | unsupported additions | clinical safety | overall | aligned | falls-risk match | ROUGE-L | needs review | words (ref mean 696) |
|---|---|---|---|---|---|---|---|---|---|
| 4.40 | 4.25 | 3.85 | 4.00 | 4.05 | **4/10** | 8/10 | 0.157 | 5/10 | **1419** |

Per case:

| case | overall | aligned votes | falls risk (v0.3 / ref) | review |
|---|---|---|---|---|
| 032 | 3.5 | 1/2 | **Moderate / High** | ✓ |
| 033 | 4.5 | 1/2 | Moderate / Moderate | ✓ |
| 035 | 4.0 | 1/2 | Moderate / Moderate | ✓ |
| 046 | 4.5 | 2/2 | Moderate / Moderate | |
| 057 | 4.0 | 2/2 | High / High | |
| 064 | 3.5 | 0/2 | **Moderate / High** | |
| 066 | 4.5 | 2/2 | Moderate / Moderate | |
| 067 | 4.5 | 2/2 | High / High | |
| 072 | 4.0 | 1/2 | Moderate / Moderate | ✓ |
| 083 | 3.5 | 1/2 | Moderate / Moderate | ✓ |

The judges reported 73 errors. The major ones were:
- 7 risk_interpretation, mainly the falls-risk downgrades in 032 and 064 and the under-weighting of O&M in 072
- 4 omission
- 3 hallucination: an unsupported low-vision referral and invented home or social details in 064 and 083

The remainder were minor: 33 omissions, 13 hallucinations, 10 terminology_drift and 2 tone_register.

**The two judges differ a lot in strictness:**

| judge | mean overall | aligned rate | mean unsupported_additions |
|---|---|---|---|
| gpt-5-mini | 4.6 | 9/10 | 4.8 |
| gpt-5.4-mini | 3.5 | 4/10 | 2.9 |

gpt-5-mini looks lenient. Because a tie counts as not aligned, the final aligned rate is effectively set by the stricter judge. This is the intended conservative behaviour, but it should be considered when choosing the Ollama judge pair.

---

## 3. Faults seen in v0.3

The counts below come from text search over the 10 v0.3 outputs and the 10 OT references.

### 3.1 Faults in the v0.3 outputs (from the baseline run)

| # | Fault | v0.3 outputs | References | Example |
|---|---|---|---|---|
| F1 | **Prompt rule labels repeated as headings.** Section 4 is laid out as rules A–O copied from the prompt rather than OT subsections. This is the main recurring/templated statement. | **10/10** (121 headings) | 0/10 | 064: "A. ASSESS BEFORE PRESCRIBING … B. ENVIRONMENTAL ASSESSMENT AND MODIFICATION … K. LOW VISION SERVICE … N. FEASIBILITY … O. PRIORITISATION" |
| F2 | **Unrequested content after Section 6**: notes, next steps, disclaimers, the internal quality checklist, offers of help | **10/10** | 0/10 | 032: "Notes and next steps for the OT clinician… Final checks: - Case is handled independently (032)… If you would like, I can condense this into a shorter one-page OT handover" |
| F3 | **Raw optometry measurements copied**: v0.3 only forbids this in Key Vision Issues, so the model puts them in Patient Context | **10/10** (46 values) | 0/10 | 046: "presenting 6/30, best correction 6/24… habitual N14 OU; N10 OU with add… 1.20 log units" |
| F4 | **Low-vision service referral added by default**, including for correctable or already-managed impairment. Judges flagged it as a hallucination in 064 and 083. | **10/10** (29 mentions) | 1/10 | 033 (correctable refractive blur): "…low-vision services if indicated"; 064: "consider referral to low-vision rehabilitation" |
| F5 | **Driving over-emphasised and repeated** across Patient Context, Section 4 and Section 6 | 92 mentions (4–13 per case) | 31 | 083: 13 driving mentions |
| F6 | **Confirmed fall downgraded to Moderate.** v0.3 says only "Avoid defaulting automatically to High". | 2 of 4 confirmed-fall cases (032, 064) | Confirmed fall → High in 4/4 | 032: "recurrent outdoor falls… Moderate" |
| F7 | **Same recommendation restated in several sections**: contributes to length of about 2× the references | 1419 words | 696 words | 064: O&M, cane and low-vision points repeated in Sections 4, 6 and "Notes" |
| F8 | **No emergency communication / personal alarm** | **0/10** | 6/10 | ref 032: "Falls alarm may be considered… when alone at home or in the community" |
| F9 | **No information gaps flagged** | **0/10** | 3/10 | ref 057: "Clarify whether this reflects never having driven or a change in driving status" |
| F10 | **Mobility aids not linked to identification as vision-impaired** | 0/10 | 4/10 | ref 072: "identifying self as having vision impairment in public such as with low vision badge or white cane" |
| F11 | **Useful mobility routines dropped entirely**, because v0.3 discourages scripted routines | 1/10 | 6/10 (kept, mostly framed under O&M) | ref 064: "O&M intervention… may include: Train: pause before turning → scan to left wall/doorframe…" |

F8–F11 were first identified by diffing the Stage 1 drafts (v0.2 output) against the OT-corrected references. The v0.3 run confirms that v0.3 still does not produce them.

### 3.2 What v0.3 already handles well
- **O&M is considered in 10/10 outputs**, against 0/10 Stage 1 drafts.
- **Lighting, glare and contrast** are covered in 10/10.
- **Non-visual strategies** are covered in 10/10.
- **Factual consistency is high** (4.25), and **coverage is high** (4.40).

The v0.3 rules for task-level ADL/IADL translation, environment and O&M work as intended. v0.4 therefore leaves them alone.

### 3.3 Not changed (case-specific, would risk overfitting)
- Council pavement advocacy (033)
- Gym access (035)
- Distinguishing hemianopia from neglect (064)
- MyAgedCare: Australia-specific, and already covered generically by v0.3 rule G

---

## 4. What v0.4 improves

v0.4 is v0.3 plus small, generic insertions. Nothing was removed, and v0.3 is unchanged. Each change maps to a fault from §3.

| Fault | v0.4 change | Where in prompt |
|---|---|---|
| F1 | "Rules A–O below are reasoning guidance for this section. Do NOT use their letters or titles… as headings in the output; use only the subsection names listed above." | Section 4 intro |
| F2 | "End the output after Section 6. Do NOT append notes, next steps, disclaimers, the results of the quality checks below, or offers of further help." + "These checks are internal; do not include them in the output." | Section 6, Final Quality Check |
| F3 | Raw-measurement rule extended to "anywhere in the summary, including Patient Context" with examples (acuity values, contrast scores, IOP, prism values, cup-disc ratios) | Key Vision Issues |
| F4 | Low-vision liaison "only… when reduced vision is not correctable with spectacles or current management and it affects detail-dependent tasks; do not add low-vision referral by default" | Rule K |
| F5 | Driving: "State it once there and keep it brief; do not repeat driving content in other sections." | Rule I.5 |
| F6 | Falls-risk anchor. **High**: a confirmed fall linked to the vision impairment, or severe uncorrectable impairment. **Moderate**: near-misses, stumbles, collisions or hesitancy without a fall. **Low**: mild or corrected impairment. Plus "do not downgrade a confirmed vision-related fall". | Section 5 |
| F7 | "State each recommendation once, in the most relevant section… Section 6 only summarises." | Variation rule |
| F8 | Support rule adds "ability to summon help in an emergency (phone accessibility, personal/falls alarm) where falls risk or time spent alone makes this relevant" | Rule G |
| F9 | New **rule 10 INFORMATION GAP RULE**: state what the OT should clarify (driving history, stroke extent, hearing severity, carer role, support capacity) instead of assuming it, and only when it would change planning | After rule 9 |
| F10 | O&M list: "mobility aids, including their role in identifying the person to others as having vision impairment" | Rule D |
| F11 | "Where an example routine is clinically useful, present it as an example of what O&M training may include… not as an OT-prescribed script." | Rule D |

**Two caveats:**
- **The F6 anchor comes from the references.** It matches all 10 development cases: the 4 cases with a confirmed fall are High, and the 6 without are Moderate. Because it encodes a clinical rule taken from the reference standard, the OT team should confirm it before the configuration is frozen.
- **v0.4 has not been benchmarked yet.** These changes target faults observed with gpt-5-nano. Run v0.4 with the same judges, and with the Ollama candidates, to confirm that the faults are reduced. The deterministic counts in §3.1 can be re-run directly on the new outputs.

---

## 5. Next steps
1. On the server, set the Ollama candidates and 2 fixed judges in `main.py`. The judges should be larger than the candidates and ideally from different model families. Run with `prompt_version="0_3"`.
2. Run the same models with `prompt_version="0_4"` under a new `run_name`, and compare `summary.csv` and the §3.1 fault counts.
3. Confirm the falls-risk anchor (F6) with the OT team.
4. Consider 3 generations per case for model selection; currently it is 1.
5. Stage 2A.2 (knowledge tables) is not started.
