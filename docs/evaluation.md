# Evaluation Results

**Generated:** 2026-08-17T19:03:48.666588+00:00 · **Reproduce:** `python -m backend.app.evaluate`

Every number on this page is computed by `backend/app/evaluate.py`. None is hand-written.
All data is synthetic.

## Dataset

| | |
|---|---|
| Transactions | 90,258 |
| Fraud | 3,459 (3.83%) |
| Cards / merchants | 1,650 / 263 |
| Window | 44 days |
| Attack vectors | 25 across 10 categories |

## Split

**temporal with delay block.** Train 58,667 · Test 27,078 · delay gap
5% of the timeline discarded between them, reflecting late label
arrival. Test-set fraud rate 2.98%.

## Discrimination

| Metric | Value |
|---|---|
| **PR-AUC** (headline) | **0.9435** (95% CI 0.9312–0.9572) |
| ROC-AUC | 0.9894 |

PR-AUC is the headline; ROC-AUC is reported for comparability and is optimistic under imbalance.

## Operating points

**Best F1** (threshold 0.798): precision 0.972,
recall 0.891, F1 0.929, FPR 0.0008.
Confusion — TP 718, FP 21,
FN 88, TN 26251.

**Capacity-constrained** (1% review budget, 271 alerts):
recall 0.334, precision 0.993. recall achievable within a 1% daily review budget.

> ⚠️ Recall here is BOUNDED BY THE BUDGET, not by the model: with a 1% alert budget and 2.98% test prevalence, no detector could exceed the ceiling shown. Read this number as 'value captured per unit of analyst effort', not as model recall. Ceiling for this split: **0.336**.

**Prevalence-matched** (2.98% budget, 806 alerts):
recall 0.909, precision 0.909. alert budget sized to actual prevalence, so recall is not budget-capped and reflects the detector rather than the queue.

### Prevalence caveat

Synthetic fraud prevalence here is 3.83%, deliberately higher than the ~0.1-1% seen in live card portfolios (PSD2 RTS Annex reference bands are 1-13 bps; Stripe reports ~1 in 1,000). A higher rate is required to train and evaluate 25 distinct attack vectors on a synthetic corpus. Threshold-dependent metrics (precision, alert-rate recall, insult rate) are prevalence-sensitive and would shift in a live portfolio; PR-AUC, calibration and latency are the more transferable figures.

## Money and customer impact

| Metric | Value |
|---|---|
| Value detection rate | 0.941 |
| Fraud value attempted | 315,181.41 |
| Fraud value stopped | 296,581.20 |
| Insult rate | 0.0008 |

> Absolute values are summed over `amount` across a multi-currency synthetic population,
> so they carry no single currency unit. Read the **ratio** (value detection rate), not the
> absolute totals.

## Fidelity evidence (criterion 2)

Fidelity is judged instrumentally, so it is measured rather than asserted.
9/9 marginals within published reference bands; max raw-field univariate AUC 0.8958, mean attack/legit overlap 0.6557.

### Generated marginals vs published reference bands

| Measure | Value | Reference band | In band |
|---|---|---|---|
| legit baseline fraud bps | 0.0 | 0.0–60.0 | yes |
| cnp share | 0.42365 | 0.3–0.6 | yes |
| cross border share | 0.10309 | 0.03–0.2 | yes |
| night share | 0.03422 | 0.02–0.18 | yes |
| benford mad | 0.00101 | 0.0–0.015 | yes |
| log amount abs skew | 0.00471 | 0.0–1.0 | yes |
| dispersion index | 35.22185 | 1.0–400.0 | yes |
| mcc gini | 0.44472 | 0.25–0.85 | yes |
| mean primary device share | 0.97024 | 0.55–1.0 | yes |

Bands are sourced from public references (PSD2 RTS Annex fraud-rate bands, Nigrini's MAD
thresholds for Benford conformity) and are deliberately wide — they are sanity bands for a
synthetic corpus, not targets to overfit.

### Non-separability of attack traffic

If attacks came from an obviously different process, any classifier would score ~1.0 and the
whole evaluation would be meaningless. Measured on **raw** authorization fields, not
engineered features:

| Raw field | Univariate AUC | Attack/legit overlap |
|---|---|---|
| cross_border | 0.896 | 0.208 |
| card_present | 0.788 | 0.424 |
| merchant_age_days | 0.706 | 0.550 |
| hour_of_day | 0.651 | 0.667 |
| amount | 0.559 | 0.860 |
| network_token_used | 0.552 | 0.895 |
| is_recurring | 0.507 | 0.986 |

Max univariate AUC **0.8958**, mean attack/legit overlap
**0.6557**. Univariate AUC is measured on RAW authorization fields, not engineered features. A max well below 1.0 means no single field betrays the attacks, so the reported detection performance comes from the feature layer and cascade rather than from a generation artefact. High overlap on the hard-by-design vectors is the intended result, not a defect.

Most camouflaged vectors (highest overlap with legitimate traffic):
- `VELOCITY_EVASION` — mean overlap 0.691
- `GENAI_DOC_FARM` — mean overlap 0.640
- `TRA_THRESHOLD_GAMING` — mean overlap 0.636
- `AGENT_IMPERSONATION` — mean overlap 0.626
- `ATO_CREDENTIAL_STUFF` — mean overlap 0.615

## Calibration

Brier 0.00445 · ECE (10-bin) 0.00378 · method: isotonic regression on a held-out temporal slice.

| Bin | n | Predicted | Observed |
|---|---|---|---|
| 0.0-0.1 | 26021 | 0.001 | 0.002 |
| 0.1-0.2 | 60 | 0.119 | 0.117 |
| 0.2-0.3 | 142 | 0.237 | 0.063 |
| 0.4-0.5 | 4 | 0.459 | 0.250 |
| 0.5-0.6 | 52 | 0.528 | 0.173 |
| 0.6-0.7 | 55 | 0.636 | 0.218 |
| 0.7-0.8 | 6 | 0.766 | 0.333 |
| 0.8-0.9 | 29 | 0.845 | 0.552 |
| 0.9-1.0 | 709 | 0.999 | 0.989 |

## Latency

Two costs, reported separately because they behave differently in production.

| | |
|---|---|
| **Inline decision** (rules + model + graph + arbiter, features supplied) | **p50 13.65 ms · p95 16.23 ms · p99 18.79 ms** |
| Batch feature recompute, amortised | 0.0854 ms/row |

n=150, context 2,000 rows. decision_* is the inline path with features supplied; the batch feature recompute is reported separately and would be incremental in production.

Cascade: the graph stage evaluates 20.0% of traffic.

## Zero-day generalisation

The hardest question for a closed-loop system: **can the defence catch fraud typologies it
has never seen?** 6 attack vectors were removed from training
entirely, then scored at an operating point calibrated on seen traffic only
(threshold 1.000).

**Recall on unseen vectors: 0.718** across 975
transactions.

| Held-out vector | n | Recall | Mean risk | Hard by design |
|---|---|---|---|---|
| AGENT_IMPERSONATION | 216 | 0.116 | 0.866 | no |
| ROMANCE_PIG_BUTCHERING | 144 | 0.500 | 0.931 | yes |
| APP_SCAM_LLM | 30 | 0.800 | 0.988 | yes |
| ATO_CREDENTIAL_STUFF | 117 | 0.974 | 0.997 | no |
| SYNTH_ID_BUSTOUT | 168 | 0.982 | 0.999 | no |
| BIN_ENUMERATION_BURST | 300 | 1.000 | 1.000 | no |

recall on fraud typologies entirely absent from training, measured at an operating point calibrated on seen traffic only.

## Per-attack recall at the capacity-constrained operating point

Sorted worst-first — the hard cases are meant to be hard.

| Attack | Category | n | Recall | Mean risk | Hard by design | Severity |
|---|---|---|---|---|---|---|
| REFUND_ABUSE_COLLUSION | Merchant fraud | 2 | 0.000 | 0.846 | no | 3 |
| ADAPTIVE_MIMICRY | Adaptive evasion | 68 | 0.015 | 0.224 | yes | 5 |
| SIM_SWAP_OTP | Account takeover | 24 | 0.042 | 0.272 | yes | 5 |
| DEEPFAKE_KYC_ONBOARD | Deepfake / KYC | 40 | 0.825 | 0.984 | no | 5 |
| TRA_THRESHOLD_GAMING | Adaptive evasion | 48 | 0.854 | 0.995 | yes | 4 |
| VOICE_CLONE_ATO | Account takeover | 28 | 0.893 | 0.996 | no | 5 |
| APP_SCAM_LLM | Scam / social engineering | 10 | 0.900 | 0.985 | yes | 5 |
| SCA_EXEMPTION_ABUSE | Adaptive evasion | 110 | 0.909 | 0.982 | yes | 4 |
| VELOCITY_EVASION | Adaptive evasion | 72 | 0.931 | 0.998 | yes | 4 |
| GENAI_DOC_FARM | Synthetic identity | 40 | 0.950 | 0.992 | no | 4 |
| ATO_CREDENTIAL_STUFF | Account takeover | 38 | 1.000 | 1.000 | no | 4 |
| FAKE_STOREFRONT | Merchant fraud | 23 | 1.000 | 1.000 | no | 4 |
| ROMANCE_PIG_BUTCHERING | Scam / social engineering | 48 | 1.000 | 1.000 | yes | 5 |
| INVOICE_REDIRECT_BEC | Scam / social engineering | 4 | 1.000 | 1.000 | yes | 4 |
| CARD_TESTING_MICRO | Enumeration | 80 | 1.000 | 1.000 | no | 3 |
| BIN_ENUMERATION_BURST | Enumeration | 100 | 1.000 | 1.000 | no | 3 |
| MULE_FANOUT | Fraud ring | 31 | 1.000 | 1.000 | no | 5 |
| AGENT_PROMPT_INJECTION | Agentic commerce | 8 | 1.000 | 1.000 | no | 4 |
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
