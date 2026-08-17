# Detection Methodology

How the defence works, why each choice was made, and what the evidence says. Results live in
[`evaluation.md`](evaluation.md) (generated). Rejected alternatives are in
[`decisions.md`](decisions.md).

---

## 1. The problem shape

Payment fraud detection is not a generic classification task. Four properties dictate the
architecture:

| Property | Consequence |
|---|---|
| **Extreme class imbalance** (real portfolios run 1–13 basis points) | Accuracy is meaningless; PR-AUC is the honest headline |
| **Inline latency budget** | The decision path must be milliseconds, not seconds — which excludes LLMs from the decision |
| **Labels arrive weeks late** | Random splits leak the future; a delay block is required |
| **Adversary adapts** | Static evaluation overstates durability; held-out attack types are the real test |
| **Finite analyst capacity** | Unconstrained recall is a fiction; recall at a fixed alert budget is the operational number |

## 2. Feature design

57 features, all strictly causal. Four families:

### 2.1 Multi-horizon velocity
`card_txn_1h/24h/7d`, `card_amt_24h/7d`, `dev_txn_1h/24h`, `ip_txn_24h`, `mch_txn_1h`.

The workhorse of production systems. Computed with `searchsorted` over sorted timestamps,
excluding the current row — exact, and cheap.

### 2.2 Deviation from the entity's own baseline
`card_amt_z`, `card_amt_ratio`, `card_history_len`, `card_secs_since_prev`,
`card_cadence_std`, `card_new_merchant/device/country`.

**This is the family that matters most**, and the reason is in the threat model: account
takeover, APP scams and mimicry all present *genuine credentials*. A population-level
anomaly detector cannot see them. Deviation from the entity's own history can.

Running moments come from shifted cumulative sums, so the first event for a card correctly
has no history (`card_history_len == 0`, `card_secs_since_prev == -1`).

### 2.3 Neighbour aggregation over shared entities
`dev_prior_cards`, `ip_prior_cards`, `ua_prior_cards`, `mch_prior_cards`,
`card_prior_devices`.

Prior distinct-count of the counterparty entity. One device touching many cards is the
clearest ring signal available at the authorization layer.

**Why this instead of a GNN:** GADBench found tree ensembles with simple neighbourhood
aggregation outperform GNNs tailored for graph anomaly detection. We took the benchmark's
recommendation rather than the fashionable choice — see `decisions.md` D3.

### 2.4 Verification and exemption posture
`threeds_authenticated/failed/na`, `avs_fail`, `cvv_fail`, `sca_low_value/tra/corporate`,
`entry_magstripe/keyed/cof`, `network_token`, `cross_border`, `band_proximity`.

Where payments realism lives. `band_proximity` measures distance below the nearest PSD2
exemption threshold (€30/€100/€250/€500) — attackers gaming banded logic cluster just
underneath, so proximity-from-below is itself the signal.

### 2.5 Causality guarantee

No whole-column aggregate, no target encoding, no future information. Proven, not asserted:

```python
def test_features_are_causal(...):
    full = build_features(df)
    prefix = build_features(df.iloc[:cut])
    assert_frame_equal(full.iloc[:cut], prefix)   # exact
```

If any feature peeked at the future, recomputing on a time prefix would disagree with the
full run. This test is the single most important guard in the project, because leakage
produces excellent offline numbers and useless production behaviour.

## 3. The cascade

```
        all traffic          all traffic            top 20%
            │                     │                    │
        ┌───▼────┐           ┌────▼─────┐         ┌────▼─────┐
        │ RULES  │           │  MODEL   │         │  GRAPH   │
        │ 39 sig │           │ HistGBM  │         │ components│
        └───┬────┘           └────┬─────┘         └────┬─────┘
            │  s_rules            │ p_model            │ s_graph, ring
            └─────────────┬───────┴────────────────────┘
                          ▼
                  ARBITER (logistic)
                          ▼
                ISOTONIC CALIBRATION
                          ▼
              risk score → band → action
```

### Stage 1 — Rules (39 named signals)

Deterministic predicates over causal features, each with a weight, aggregated through a
saturating transform (`1 − e^(−Σw/3)`) so many weak signals never masquerade as certainty.

**Why rules first.** They are auditable, deployable in hours, and what fraud teams actually
trust. Uber *generates* rules from pattern mining and has analysts approve them for exactly
this reason. Sardine frames the core tension precisely: attackers "mutate in milliseconds"
while shipping a rule change takes about a week.

**The critical design detail:** signal names are aligned to the taxonomy's
`expected_detection_signals`. That alignment is what makes per-signal recall possible — the
ability to ask *did we catch this for the right reason?*

### Stage 2 — Model (`HistGradientBoostingClassifier`)

57 features, 300 iterations, `class_weight="balanced"`, L2 regularisation, no early stopping
(so training is deterministic).

**Why gradient-boosted trees.** Consistent evidence that they match or beat deep tabular
models; an industry study found learned sequence embeddings added *nothing* over a boosted
tree with domain features (0.9205 → 0.9245).

**Why sklearn's implementation.** LightGBM requires an OpenMP runtime unavailable in this
environment. `HistGradientBoostingClassifier` is the same algorithm family with no native
dependency — a constraint that cost nothing in capability.

### Stage 3 — Graph (gated)

Connected components over a heterogeneous graph of card ↔ device / network-prefix /
merchant edges. Component card-count drives a saturating score; components with ≥5 cards
raise a `ring_component` flag.

**Why gated to 20%.** This is the expensive stage and it only earns its cost on traffic that
already looks suspicious. Gating is by **compute budget**, not score threshold — our first
implementation used an absolute `≥0.15` cutoff and silently degenerated into running on 100%
of traffic, because most legitimate transactions fire at least one weak rule.

### Arbitration

A logistic regression over five component scores:

```
[ logit(p_model), s_rules, s_graph, ring_flag, injection_flag ]
```

`p_model` enters as a **logit** so the arbiter combines comparable log-odds quantities
rather than mixing a probability with two bounded scores.

**Why an arbiter rather than a fixed weighted blend.** It is learned, it is five parameters
(so it cannot overfit meaningfully), and its coefficients are exact — which is what makes
the explanation additive and true by construction.

### Calibration

Isotonic regression on a held-out temporal slice.

**Why mandatory.** Random undersampling can drive ECE from 0.008 to 0.395; without
calibration a threshold has no interpretable meaning. With it, "block above 0.9" implies
roughly a 1-in-10 false-block rate — a statement a risk owner can actually reason about.

Measured: **ECE 0.0038, Brier 0.0045.**

### Three disjoint temporal slices

| Slice | Fits | Reason |
|---|---|---|
| First 60% | Model | — |
| Next 20% | Arbiter | Never sees the model's training data, so it does not inherit the model's optimism |
| Final 20% | Calibrator | Never sees the arbiter's training data, so calibration is honest |

## 4. Risk scoring and action

| Score | Band | Action | Intent |
|---|---|---|---|
| ≥ 0.85 | CRITICAL | `BLOCK` | Decline the authorization |
| ≥ 0.60 | HIGH | `STEP_UP` | Force strong authentication |
| ≥ 0.30 | MEDIUM | `REVIEW` | Queue for analyst review |
| < 0.30 | LOW | `ALLOW` | Approve |

Because scores are calibrated, these thresholds can be re-derived from a cost model
(fraud loss vs insult cost) rather than chosen by feel.

Every decision at HIGH or above carries at least one named signal — asserted in the test
suite, because a block with no explanation is operationally unusable.

## 5. Evaluation methodology

### 5.1 Splitting

Temporal, with a **delay block**: train on the earliest 65%, discard the next 5% of the
timeline, test on the remainder. The discarded block encodes that chargeback and
investigator labels arrive weeks late.

Attack campaigns are scheduled in three rotated waves across the window so every vector
appears on both sides of the split. Without that, a temporal split silently becomes a
held-out-attack-type experiment — which we then run *deliberately* and separately.

### 5.2 Metrics, and why each exists

| Metric | Why |
|---|---|
| **PR-AUC** (headline, with bootstrap 95% CI) | The correct summary under heavy imbalance |
| ROC-AUC | Reported for comparability, and labelled as optimistic |
| Best-F1 operating point | Conventional reference point |
| **Recall at a 1% alert budget** | The operational question: what does an analyst team actually catch? Reported *with its mathematical ceiling*, because at 3.8% prevalence a 1% budget caps recall at 0.336 regardless of model quality |
| Prevalence-matched operating point | Recall when the budget is not the binding constraint |
| **Value detection rate** | Fraud is a money problem, not a count problem |
| **Insult rate** | False declines have a real customer cost |
| **Calibration** (Brier, ECE, reliability diagram) | Makes thresholds meaningful |
| **Latency** p50/p95/p99, split into decision vs feature-build | The inline path is what matters; folding batch feature cost into a headline would misrepresent the architecture |
| **Per-attack recall** | Aggregates hide which typologies are missed |
| **Per-signal recall** | Was it caught for the *right reason*? |
| **Zero-day recall** | The only honest test of generalisation to novel fraud |

A 2026 survey of 49 sources found that among 18 fraud sources, **none** reported latency,
cost or calibration. Reporting all three is unusually cheap credibility.

### 5.3 What we deliberately do not do

- **No SMOTE or resampling** — degrades performance on multimodal minorities and leaks when
  applied before splitting (`decisions.md` D4)
- **No accuracy** as a headline — meaningless at this imbalance
- **No LLM-as-judge** — unreliable, with documented identity-aware bias
- **No hand-written metrics** — every number originates in `evaluate.py`

## 6. Honest limitations

1. **Synthetic-to-real transfer is unproven.** The schema follows real message standards and
   prevalence is anchored to regulator reference rates, but no synthetic corpus proves
   live-portfolio performance. Threshold-dependent metrics would shift; PR-AUC, calibration
   and latency transfer better than precision at a fixed threshold.
2. **Prevalence is elevated (3.8%)** relative to live portfolios (1–13 bps), because 25
   distinct vectors need enough positives per vector to evaluate. The metrics artifact states
   this explicitly.
3. **Adaptive vectors have materially lower recall** — `ADAPTIVE_MIMICRY` most of all. That
   is by design (it is built to be near-invisible) and it is reported worst-first rather than
   averaged away.
4. **Five declared signals are unimplementable** at the authorization layer — dispute
   lifecycle and session telemetry. Named in `UNIMPLEMENTED_SIGNALS` and surfaced in the report.
5. **No per-row attribution inside the model.** Claimed nowhere; the caveat ships with every
   explanation.
6. **The feedback loop is unsolved.** Blocked transactions never yield labels. We model delay,
   not the poisoning it causes.
7. **Feature computation is batch.** Production needs an incremental streaming feature store;
   the reported decision latency assumes features are supplied, which is stated in the metrics.
