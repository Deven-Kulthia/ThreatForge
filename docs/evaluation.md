# Evaluation Results

**Generated:** 2026-08-17T15:21:48.139894+00:00 · **Reproduce:** `python -m backend.app.evaluate`

Every number on this page is computed by `backend/app/evaluate.py`. None is hand-written.
All data is synthetic.

## Dataset

| | |
|---|---|
| Transactions | 90,256 |
| Fraud | 3,457 (3.83%) |
| Cards / merchants | 1,650 / 263 |
| Window | 44 days |
| Attack vectors | 25 across 10 categories |

## Split

**temporal with delay block.** Train 58,666 · Test 27,077 · delay gap
5% of the timeline discarded between them, reflecting late label
arrival. Test-set fraud rate 2.98%.

## Discrimination

| Metric | Value |
|---|---|
| **PR-AUC** (headline) | **0.9569** (95% CI 0.9455–0.9689) |
| ROC-AUC | 0.9955 |

PR-AUC is the headline; ROC-AUC is reported for comparability and is optimistic under imbalance.

## Operating points

**Best F1** (threshold 0.885): precision 0.989,
recall 0.885, F1 0.934, FPR 0.0003.
Confusion — TP 715, FP 8,
FN 93, TN 26261.

**Capacity-constrained** (1% review budget, 271 alerts):
recall 0.334, precision 0.996. recall achievable within a 1% daily review budget.

> ⚠️ Recall here is BOUNDED BY THE BUDGET, not by the model: with a 1% alert budget and 2.98% test prevalence, no detector could exceed the ceiling shown. Read this number as 'value captured per unit of analyst effort', not as model recall. Ceiling for this split: **0.335**.

**Prevalence-matched** (2.98% budget, 808 alerts):
recall 0.918, precision 0.918. alert budget sized to actual prevalence, so recall is not budget-capped and reflects the detector rather than the queue.

### Prevalence caveat

Synthetic fraud prevalence here is 3.83%, deliberately higher than the ~0.1-1% seen in live card portfolios (PSD2 RTS Annex reference bands are 1-13 bps; Stripe reports ~1 in 1,000). A higher rate is required to train and evaluate 25 distinct attack vectors on a synthetic corpus. Threshold-dependent metrics (precision, alert-rate recall, insult rate) are prevalence-sensitive and would shift in a live portfolio; PR-AUC, calibration and latency are the more transferable figures.

## Money and customer impact

| Metric | Value |
|---|---|
| Value detection rate | 0.913 |
| Fraud value attempted | 329,366.02 |
| Fraud value stopped | 300,767.99 |
| Insult rate | 0.0003 |

## Calibration

Brier 0.00352 · ECE (10-bin) 0.00193 · method: isotonic regression on a held-out temporal slice.

| Bin | n | Predicted | Observed |
|---|---|---|---|
| 0.0-0.1 | 26033 | 0.001 | 0.002 |
| 0.1-0.2 | 99 | 0.107 | 0.101 |
| 0.2-0.3 | 134 | 0.234 | 0.112 |
| 0.4-0.5 | 1 | 0.407 | 0.000 |
| 0.5-0.6 | 61 | 0.500 | 0.295 |
| 0.7-0.8 | 26 | 0.722 | 0.385 |
| 0.8-0.9 | 15 | 0.885 | 0.733 |
| 0.9-1.0 | 708 | 1.000 | 0.994 |

## Latency

Two costs, reported separately because they behave differently in production.

| | |
|---|---|
| **Inline decision** (rules + model + graph + arbiter, features supplied) | **p50 16.58 ms · p95 25.93 ms · p99 31.36 ms** |
| Batch feature recompute, amortised | 0.1017 ms/row |

n=150, context 2,000 rows. decision_* is the inline path with features supplied; the batch feature recompute is reported separately and would be incremental in production.

Cascade: the graph stage evaluates 20.0% of traffic.

## Zero-day generalisation

The hardest question for a closed-loop system: **can the defence catch fraud typologies it
has never seen?** 6 attack vectors were removed from training
entirely, then scored at an operating point calibrated on seen traffic only
(threshold 1.000).

**Recall on unseen vectors: 0.781** across 973
transactions.

| Held-out vector | n | Recall | Mean risk | Hard by design |
|---|---|---|---|---|
| AGENT_IMPERSONATION | 216 | 0.190 | 0.570 | no |
| ROMANCE_PIG_BUTCHERING | 144 | 0.764 | 0.893 | yes |
| APP_SCAM_LLM | 30 | 0.933 | 0.977 | yes |
| ATO_CREDENTIAL_STUFF | 115 | 0.983 | 0.992 | no |
| BIN_ENUMERATION_BURST | 300 | 1.000 | 1.000 | no |
| SYNTH_ID_BUSTOUT | 168 | 1.000 | 1.000 | no |

recall on fraud typologies entirely absent from training, measured at an operating point calibrated on seen traffic only.

## Per-attack recall at the capacity-constrained operating point

Sorted worst-first — the hard cases are meant to be hard.

| Attack | Category | n | Recall | Mean risk | Hard by design | Severity |
|---|---|---|---|---|---|---|
| SIM_SWAP_OTP | Account takeover | 24 | 0.000 | 0.275 | yes | 5 |
| REFUND_ABUSE_COLLUSION | Merchant fraud | 2 | 0.000 | 0.500 | no | 3 |
| ADAPTIVE_MIMICRY | Adaptive evasion | 67 | 0.030 | 0.232 | yes | 5 |
| VELOCITY_EVASION | Adaptive evasion | 72 | 0.917 | 0.978 | yes | 4 |
| DEEPFAKE_KYC_ONBOARD | Deepfake / KYC | 40 | 0.925 | 0.991 | no | 5 |
| GENAI_DOC_FARM | Synthetic identity | 40 | 0.950 | 0.986 | no | 4 |
| ATO_CREDENTIAL_STUFF | Account takeover | 41 | 0.976 | 0.997 | no | 4 |
| TRA_THRESHOLD_GAMING | Adaptive evasion | 48 | 0.979 | 0.994 | yes | 4 |
| VOICE_CLONE_ATO | Account takeover | 28 | 1.000 | 1.000 | no | 5 |
| FAKE_STOREFRONT | Merchant fraud | 23 | 1.000 | 1.000 | no | 4 |
| APP_SCAM_LLM | Scam / social engineering | 10 | 1.000 | 1.000 | yes | 5 |
| ROMANCE_PIG_BUTCHERING | Scam / social engineering | 48 | 1.000 | 1.000 | yes | 5 |
| INVOICE_REDIRECT_BEC | Scam / social engineering | 4 | 1.000 | 1.000 | yes | 4 |
| CARD_TESTING_MICRO | Enumeration | 80 | 1.000 | 1.000 | no | 3 |
| BIN_ENUMERATION_BURST | Enumeration | 100 | 1.000 | 1.000 | no | 3 |
| MULE_FANOUT | Fraud ring | 31 | 1.000 | 1.000 | no | 5 |
| AGENT_PROMPT_INJECTION | Agentic commerce | 8 | 1.000 | 1.000 | no | 4 |
| SCA_EXEMPTION_ABUSE | Adaptive evasion | 110 | 1.000 | 1.000 | yes | 4 |
| MANDATE_REPLAY_ABUSE | Agentic commerce | 32 | 1.000 | 1.000 | yes | 5 |

## Signal coverage

39 rule signals implemented, covering
39 of 39
distinct signals the taxonomy expects. Signals we deliberately do **not** implement, and why:

- `session_duress_pattern` — requires session/interaction telemetry, outside the auth schema
- `refund_ratio_anomaly` — requires credit/refund messages, outside the auth schema
- `post_delivery_dispute` — requires dispute lifecycle data, outside the auth schema
- `repeat_claimant_pattern` — requires dispute lifecycle data, outside the auth schema
- `synchronised_timing` — covered in practice by ring_component + machine_cadence
- `graph_fanin` — emitted by the graph stage, not the rule stage
- `ring_component` — emitted by the graph stage, not the rule stage
- `injection_pattern_in_text` — emitted by the text-safety stage

Per-signal fire rates per attack are in `artifacts/metrics.json` under `per_signal_recall`.
This is how we verify an attack was caught *for the right reason* rather than by accident.
