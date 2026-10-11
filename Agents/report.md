# Stage 2A.1 — Work Report

Branch `opt`, 11 October 2026. This report covers everything changed for Stage 2A.1 (baseline benchmarking) and the reasons for each change. The sections follow the steps in `agenda/Stage_2A_Plan_Proposal.pdf` §2A.1.

| # | Plan step | Status | Where |
|---|---|---|---|
| 1 | Retrieve original generation prompt | Done (v0.2 + OT-revised v0.3 available) | `prompts/prompt_0_2.txt`, `prompts/prompt_0_3.txt` |
| 2 | Diff drafts vs corrected references → error taxonomy | Done | §2 below, `prompts/prompt_changelog.md` |
| 3 | Minimal generic prompt revisions | Done → v0.4 | `prompts/prompt_0_4.txt` |
| 4 | Benchmark candidate models | Pipeline ready, smoke-tested on 2 cases with GPT | `benchmark/` |
| 5 | Multi-LLM-as-judge + majority agreement | Done (2 judges, majority vote + human-review flag) | `benchmark/judge.py`, `prompts/judge_0_1.txt` |
| 6 | Output: selected model + baseline prompt | **Pending**: needs the server run with the Ollama candidates | `results/<run>/summary.csv` |

---

## 1. Data conversion

- All 35 `.docx` files under `Agents/` were converted to UTF-8 `.txt` with LibreOffice (headless), and the `.docx` files were deleted. The PDF was not touched.
- Before deleting, every docx was checked for tracked changes (`w:ins` / `w:del`) and comments. None were found, so the plain text loses no correction information.
- Only `data/00_Stage2A_10_Case_File_Index` and `agenda/agenda` contained tables. Their cells are now one per line, which is still readable, but the table layout is gone.
- The originals are still in git: your commit `90d6c1a all data added` contains every docx.
- The loader strips the UTF-8 BOM that LibreOffice writes.

## 2. Diff analysis: draft (v0.2 output) vs OT-corrected reference

Method: each of the 10 `before_correction/` drafts was diffed line by line against its `02_OT_Reference_Summaries/` reference. Each change was categorised with the 2A.1 taxonomy and checked for whether prompt v0.3 already addresses it.

**Headline finding: the OT corrections are almost entirely additions.** The mean length went from 248 words in the drafts to 696 in the references. Almost nothing was deleted as wrong, and there was no systematic hallucination. The drafts were under-developed rather than incorrect.

### 2.1 Patterns already covered by v0.3

These recur across most cases, and the OT team's v0.3 already contains rules for each:

| Pattern (taxonomy) | Example of OT correction | v0.3 rule |
|---|---|---|
| Omission: task-level ADL/IADL | 032: "measuring and pouring liquids, food prep… dispensing medications… stepping in/out of showers" | 5, 6 |
| Omission: environment / lighting | 035: "inadequate brightness or inappropriate colour temperature… Shadowing… can be mistaken for an obstacle" | B, C |
| Omission: O&M referral (9 of 10 references, 0 drafts) | 067: "Seek Orientation and Mobility specialist referral" | D |
| Omission: support / participation / transport | 066: "community bus or public transport"; 072: "MyAgedCare" | G, H, I |
| Omission: magnification via eye-care pathway | 046, 067, 072: "Orthoptic assessment/review for magnification" | K |
| Terminology | Section 6 renamed "Summary of Key OT Considerations from Vision Findings" | Output format |

### 2.2 Recurring patterns v0.3 does not fully cover, which v0.4 now addresses

The counts come from text search over the 10 references and the 10 drafts.

**(a) Emergency communication / personal alarm**: in 6/10 references (032, 046, 057, 064, 066, 067), 0/10 drafts
- 032: "Falls alarm may be considered where indicated by the client's circumstances and falls risk, including when alone at home or in the community."
- 046: "Review phone use, as ability to call for support and assistance is crucial… Personal alarm may be considered."
- 067: "OT to assess ability to communicate using phone/s, particularly ability to call for assistance in an emergency."
- In v0.3 this appeared only as one line in the Final Sweep ("falls alarm or emergency communication where genuinely relevant"). Given that 6 of 10 references added it, it belongs in the support rule (G).

**(b) Information gaps the OT should clarify**: in 3/10 references (057, 064, 067), 0/10 drafts, and no v0.3 rule
- 057: "The optometry report states that the client is not driving. Clarify whether this reflects never having driven or a change in driving status"
- 057: "Consider obtaining additional information on location of strokes… cognitive, physical and/or language difficulties"; "Additional information on severity of hearing impairment may be important"
- 064: "Clarify when/why driving ceased and current licence status"
- 067: "Establish whether the client provides care or support for his partner"
- v0.3's anti-overreach rule correctly forbids *inventing* this information. Nothing tells the model to *flag* it instead, so a model following v0.3 is likely to stay silent on it.

**(c) Scripted mobility routines are re-framed under O&M, not deleted**: the drafts had "pause → scan → step" routines in 8/10 cases.
- Removed and replaced by an O&M referral: 066, 083.
- Kept but re-framed as what O&M may teach: 035 ("Intervention may be required to include training such as…"), 057 ("Technique may include…"), 064 ("O&M intervention… may include: Train: pause before turning…"), 067 ("Training may include: pause before outdoor step…").
- Kept next to an urgent O&M referral: 032. Kept as a behavioural habit sequence (rule L): 033.
- v0.3 rule D says routines "should NOT be used as a default". That is right as a default, but it pushes the model to drop content the OTs actually kept. v0.4 adds one sentence: where a routine is useful, present it as an example of what O&M training may include.

**(d) Mobility aids also identify the person as vision-impaired**: in 4/10 references (035, 057, 067, 072), 0/10 drafts
- 035: "Mobility aid may be beneficial for tactile detection… as well as identification of client as having low vision."
- 072: "May benefit from identifying self as having vision impairment in public such as with low vision badge or white cane."
- This is a generic O&M consideration missing from v0.3's O&M list.

### 2.3 Patterns deliberately NOT added (case-specific, would risk overfitting)

- Council/pavement maintenance advocacy (033 only)
- Gym access (035 only)
- Face recognition / social cues (057, 072, already covered by rules 9 and H)
- Distinguishing hemianopia from neglect (064 only)
- MyAgedCare (046, 072): Australia-specific and already covered generically by G ("formal support needs")

## 3. Prompt v0.4: exact changes

v0.4 is v0.3 plus 4 insertions and nothing removed. v0.3 is untouched, so both can be benchmarked side by side (`--prompt 0_3` vs `--prompt 0_4`).

```diff
+ 10. INFORMATION GAP RULE                                        (new, after rule 9)
+ Where information that would materially change OT reasoning is missing or ambiguous in the
+ source, state what the OT should clarify rather than assuming it.
+ Examples may include:
+ - whether "not driving" reflects never driving or a recent change, and why
+ - extent of a neurological event and possible cognitive, physical or language effects
+ - severity of a co-existing sensory impairment such as hearing loss
+ - whether the person also provides care or support for someone else
+ - current support capacity or formal services
+ Only flag gaps that would change OT assessment, intervention or support planning.

  D. MOBILITY AND O&M — possible O&M-relevant areas
- - mobility aids
+ - mobility aids, including their role in identifying the person to others as having vision impairment

  D. (after "A specific strategy may be retained only when: …")
+ Where an example routine is clinically useful, present it as an example of what O&M training
+ may include (for example "O&M training may include: …"), not as an OT-prescribed script.

  G. SUPPORT, CARERS AND FORMAL SERVICES
+ - ability to summon help in an emergency (phone accessibility, personal/falls alarm) where
+   falls risk or time spent alone makes this relevant
```

**Caveat:** v0.4 has not yet been shown to beat v0.3. Two smoke-test cases at temperature 1 are too few to compare them. Run both prompts on all 10 cases on the server, ideally with the selected model, before freezing.

## 4. Code changes

### 4.1 Existing service changed: `services/LLM/Ollama/Ollama.py` (+4/−2)

I added an optional `options` dict that is passed through to `ollama.generate`. Without it, Ollama uses its default context window of 2–4k tokens. The generation prompt alone is about 7k tokens and the judge input is about 4k, so Ollama would **silently truncate** both. The default is `None`, so existing callers behave exactly as before.

```python
options: Dict = None): # ollama options e.g. {"num_ctx": 16384, "temperature": 0}
...
response = ollama.generate(model = self.model_name, prompt = full_query, options = self.options)
```

`OpenAI_GPT` needed no changes. I verified it works with `gpt-5-nano-2025-08-07`, `gpt-5-mini-2025-08-07` and `gpt-5.4-mini-2026-03-17`, which accept its default `temperature=1` and `seed=42`.

### 4.2 New code: `Agents/benchmark/`

| File | Purpose |
|---|---|
| `data_loader.py` | discovers case ids, loads input + reference, loads prompts by version |
| `llm_factory.py` | `"openai:<model>"` / `"ollama:<model>"` → existing `OpenAI_GPT` / `Ollama` service, with the system prompt set |
| `judge.py` | `Judge` class: builds the judge input, parses JSON robustly, retries invalid JSON up to 2 times. `aggregate_verdicts()` combines the judges |
| `metrics.py` | deterministic supplementary metrics: falls-risk level parser, ROUGE-L F1 (no extra dependency) |
| `run_benchmark.py` | CLI: generate → judge → save, resumable by `--run_name` |
| `README.md` | usage, arguments, output layout |

Generation is the same for every model: system prompt = `prompt_0_X.txt`, user prompt = the raw optometry report, and the reference summary is never shown to the generator (as `00_Stage2A_10_Case_File_Index` requires).

### 4.3 Judge design (`prompts/judge_0_1.txt`)

- **Inputs:** the source optometry report, the reference summary and the candidate summary. The source is included so that factual consistency and hallucination can be checked against the original case, not only against the reference.
- **Scores (1–5)**, mapped to protocol §4.6:
  - `coverage` of the reference's functional content
  - `factual_consistency` with the source
  - `unsupported_additions`
  - `clinical_safety` (omissions, contradictions, inappropriate interpretation)
  - `overall`
- **`aligned`:** true when the summary is usable with at most minor edits. The rule is overall ≥ 4, clinical_safety ≥ 4 and no major error.
- **`errors`:** a list tagged with the 2A.1 taxonomy (omission, hallucination, terminology_drift, risk_interpretation, tone_register), each marked major or minor. This produces the error taxonomy automatically for each candidate model.
- The judge is told explicitly not to reward wording, order or length match.

### 4.4 Multi-judge aggregation

Judges are `gpt-5-mini-2025-08-07` and `gpt-5.4-mini-2026-03-17` by default. The CLI enforces a maximum of 2.

- Scores are the **mean** across judges.
- `aligned` is decided by **majority vote**. With 2 judges a 1–1 tie counts as **not aligned**, which is the conservative choice for clinical content.
- **`needs_review`** is set when the judges disagree on `aligned`, differ by 2 or more on `overall`, or one judge returned invalid JSON. These cases are the ones to verify manually. This follows protocol §4.3: the LLM judge must not be the sole basis for selection, and the decision process must be documented.
- Two deterministic checks do not depend on any judge: the falls-risk level must exactly match the reference, and ROUGE-L F1 is reported as a supplementary metric only. BERTScore is not included because it needs torch and model downloads. It can be added on the server.

### 4.5 Saved data: `Agents/results/<run_name>/`

| File | Content |
|---|---|
| `run_config.json` | models, judges, prompt versions **and sha256**, generation settings, git commit, Python version, host, date (protocol §5) |
| `generations/<model>/Case_<id>.txt` / `.json` | raw output, plus latency and timestamp |
| `judgements/<model>/Case_<id>__<judge>.json` | parsed verdict and **raw** judge response |
| `judge_scores.csv` | model × case × judge |
| `case_results.csv` | model × case, judges aggregated, plus metrics |
| `errors.csv` | every error the judges reported, for taxonomy analysis |
| `summary.csv` | one row per model, ranked by aligned rate, then overall |

Re-running with the same `--run_name` reuses existing files. An interrupted server run therefore resumes where it stopped, and adding a model to an existing run only generates and judges the new model.

## 5. Smoke test (`results/smoke_test/`): 2 cases, gpt-5-nano, prompt v0.4

| case | coverage | factual | additions | safety | overall | aligned votes | aligned | needs_review | falls risk (cand / ref) | ROUGE-L | words |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 032 | 4.5 | 4.5 | 4.0 | 4.5 | 4.5 | 1/2 | False | **True** | High / High | 0.16 | 1375 |
| 033 | 5.0 | 4.5 | 4.0 | 4.5 | 4.5 | 2/2 | True | False | Moderate / Moderate | 0.14 | 1646 |

What this shows:
- **The pipeline works end to end.** Every judge response was valid JSON on the first attempt.
- **The judges differ in strictness**, which is the reason for using two. On case 032, gpt-5-mini gave 5 on every criterion. gpt-5.4-mini gave 4/4/3/4/4 and flagged unsupported additions, such as public transport and headlight glare, which are not in the source. The disagreement was correctly flagged `needs_review`.
- **gpt-5-nano is verbose.** It wrote about 1,500 words against a reference of about 600–700, and it copied raw measurements (VA, stereo, prism dioptres) into Patient Context. Neither judge penalised this much. If length or editing burden matters to the OT team, it could be added as a judge criterion in `judge_0_2`. For now the `words` column makes it visible.

## 6. Commits (local only, authored by you)

```
b5198e1 Add benchmark README
6bc5644 Add LLM judge, judge prompt v0.1 and Stage 2A.1 benchmark runner with smoke test results
2a7b00c Add benchmark data loader, llm factory, metrics and ollama options passthrough
b7aa7bf Add prompt v0.4 with generic revisions from draft vs reference error taxonomy
27ea56e Add Stage 2A agents data, prompts and agenda as txt (converted from docx)
```

## 7. Open items before the server run

1. **Choose the Ollama judges.** The two judges should be larger than the candidates and ideally come from different model families, to reduce self-preference bias. Keep them fixed across all runs.
2. **Compare v0.3 and v0.4 on all 10 cases** with the same judges, then pick the baseline prompt.
3. **Run more than one generation per case.** Generation currently runs once per case (`generations_per_case: 1` in `run_config.json`). For model selection, 3 runs per case would show variance. This is not implemented yet; it would be a small loop in `generate()`.
4. **Check `torch` on the server.** `services/LLM/Ollama/Ollama.py` imports it at module level (pre-existing), so the server environment needs it.
5. **2A.2 (knowledge tables)** has not been started.
