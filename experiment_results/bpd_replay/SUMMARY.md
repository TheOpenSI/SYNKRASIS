# BPD trace replay (gpt-5-nano-2025-08-07, 1 run per arm per task, sequential)

Start: saved attempt 0 of experiment_results/lcb_nano_30, then up to 5 fix attempts.
baseline = normal feedback, trace = normal feedback + concise BPD trace of the first failing public test
(never for private failures). 3779 numbers come from ../bpd_replay_3779_rerun (the first 3779 baseline run was
hit by a code-extraction bug for a repeated code fence, fixed afterwards).

| task | attempt 0 failed | baseline | trace |
|---|---|---|---|
| abc388_g | public | pass (2 fixes) | pass (3 fixes) |
| arc190_d | public | fail | fail |
| arc194_c | public | fail | pass (4 fixes) |
| arc196_c | public | fail | fail |
| 3763 | public | pass (1) | pass (1) |
| abc391_d | private | fail | fail |
| abc392_d | private | fail | fail |
| 3779 | private | fail | fail |

Public-start: baseline 2/5, trace 3/5. Private-start: 0/3 both (no trace is ever sent for private failures).
16 traces attached, median ~6.7k chars, max ~10k chars (~2.5k tokens).
Run-to-run noise is large: abc388_g failed in the original run but passed here, arc190_d passed originally
but failed in both arms here. One task of difference is not evidence.
