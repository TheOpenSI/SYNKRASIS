# Prompt changelog (Stage 2A.1, steps 1-3)

- `prompt_0_2.txt` — original synthetic-generation prompt; produced `data/before_correction/`.
- `prompt_0_3.txt` — revised by the OT team after Stage 1 corrections (`data/02_OT_Reference_Summaries/`).
- `prompt_0_4.txt` — v0.3 plus minimal generic revisions from the draft vs reference diff below.

## Error taxonomy (draft v0.2 output vs OT-corrected reference, 10 cases)

| Category | Typical correction | Covered by v0.3? |
|---|---|---|
| Omission – task-level ADL/IADL | pouring, meal prep, medication, grooming, shower step added | Yes (rules 5, 6) |
| Omission – environment | lighting brightness/colour temperature/shadowing, contrast, clutter, handrails | Yes (B, C) |
| Omission – O&M referral | O&M added in almost every case with mobility risk | Yes (D) |
| Omission – support / participation | carer capacity, formal support, social isolation, transport alternatives | Yes (G, H, I) |
| Omission – emergency communication | phone use to call for help, personal/falls alarm (6 of 10 cases) | Partly (sweep only) -> **v0.4 G** |
| Omission – information gaps | "clarify why not driving", stroke extent, hearing severity, carer role | No -> **v0.4 rule 10** |
| Role / risk interpretation | scripted kerb/doorway routines kept but re-framed as "O&M training may include" | Partly (v0.3 discourages them outright) -> **v0.4 D** |
| Omission – identification as vision impaired | white cane / badge so the public recognises vision impairment | No -> **v0.4 D list** |
| Terminology / tone | "Key OT Considerations" -> "Summary of Key OT Considerations" | Yes |
| Hallucination | none systematic; corrections were additions, not removals | n/a |

## v0.4 changes (generic, not case-specific)

1. New rule 10 INFORMATION GAP RULE: state what the OT should clarify when missing information would change planning.
2. D (O&M): example routines are framed as what O&M training may include, not as OT-prescribed scripts.
3. D (O&M): mobility aids also identify the person to others as having vision impairment.
4. G (Support): ability to summon help in an emergency (phone accessibility, personal/falls alarm).
