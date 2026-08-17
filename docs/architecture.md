# Architecture

**Aegis** is a closed-loop adversarial AI system for GenAI-era payment fraud. It generates
attacks, trains a defence on them, and feeds the defence's failures back as new attacks.

All data is synthetic. The simulator has no network capability by construction.

---

## 1. The loop

```
        ┌──────────────────────► IDENTIFY ◄──────────────────────┐
        │              25-vector attack taxonomy                 │
        │        MITRE ATLAS-mapped · GenAI-era · payments-real   │
        │                                                        │
        │                          │ specs                       │
        │                          ▼                             │
        │                      GENERATE                          │ new attack
        │        feasible-action attack agents over               │ variants
        │        synthetic authorization traffic                  │
        │                          │ labelled stream              │
        │                          ▼                             │
        └───── defensive gaps ── DEFEND ── risk score ────────────┘
                per-signal recall   cascade + arbiter + calibration
```

Three properties make this a loop rather than a pipeline:

1. **Attacks are training data.** The detector is fit on simulated campaigns, not on a
   static dataset — `Engine.boot()` in `api.py` trains on 25 campaigns as its first act.
2. **Failures are measurable per attack and per signal.** `evaluate.py` reports recall for
   every vector *and* whether each declared signal actually fired, so a gap is identified
   specifically rather than as an aggregate score.
3. **The zero-day experiment closes it.** Vectors are held out of training entirely and
   scored, which is the honest test of whether the defence generalises to fraud it has
   never seen.

## 2. Module map

| Module | Responsibility | Key property |
|---|---|---|
| `schema.py` | Payment authorization schema | Ground-truth fields structurally separated from observable fields |
| `generator.py` | Synthetic population + legitimate traffic | Deterministic under a seed; emits no fraud |
| `attacks.py` | 25-vector taxonomy + simulators | Feasible-action constraint; full ground-truth metadata |
| `features.py` | 57 causal features | Strictly prior-event only; proven by prefix recomputation |
| `detect.py` | 3-stage cascade + arbiter | Each stage fit on a disjoint temporal slice |
| `explain.py` | Exact additive reason codes | Decomposition verified against `decision_function` |
| `evaluate.py` | Metric suite | Every reported number originates here |
| `api.py` | FastAPI + WebSocket + audit | No outbound network client anywhere |
| `frontend/` | 7-panel command centre | React 19 + Vite + Tailwind v4 + Recharts |

## 3. Data layer

### Schema (`schema.py`)

Modelled on real authorization message structure so the data is credible to a payments
practitioner, not just to a data scientist:

- **ISO 8583** — DE18 (MCC), DE22 (POS entry mode), DE39 (response code)
- **EMV** — entry modes distinguishing chip, contactless, magstripe fallback
- **3-D Secure 2** — `transStatus` values (`Y`/`A`/`N`/`C`/`U`/`X`)
- **PSD2 RTS** — SCA exemption types (low-value, TRA, recurring, corporate)
- **AVS / CVV** — real response-code vocabularies
- **Tokenization** — card identifiers are synthetic network-style tokens, never PANs

`OBSERVABLE_FIELDS` and `GROUND_TRUTH_FIELDS` are disjoint sets asserted in the test suite.
The feature builder only ever sees the former, so label leakage is impossible rather than
merely discouraged.

### Generator (`generator.py`)

Produces a synthetic population (cardholders with stable habits, merchants with category
and tenure) and legitimate traffic with:

- diurnal and weekly rhythm rather than uniform time sampling
- MCC-conditioned ticket sizes and card-present bias
- per-cardholder affinity, affluence, device stability, travel propensity
- verification fields set the way an acquirer would set them

Fraud rates are anchored to regulator and industry reference points — the PSD2 RTS Annex
gives 0.01% / 0.06% / 0.13% for ETV bands €500 / €250 / €100, and Stripe reports fraud at
roughly 1 in 1,000 payments — rather than the inflated rates common in public datasets.

**Legitimate and adversarial traffic come from independent code paths.** This matters: if
one function produced both, the detector could learn a generation artefact instead of a
fraud signal.

## 4. Attack layer (`attacks.py`)

25 vectors across 10 categories. See [`fraud-taxonomy.md`](fraud-taxonomy.md) (generated
from the code) for the full catalogue.

Each campaign emits a structured ground-truth contract:

```python
{
  "scenario_id", "attack_type", "attack_name", "category",
  "genai_role",                    # what generative AI specifically changed
  "mitre_atlas",                   # framework alignment
  "attack_strength", "severity", "hard_to_detect",
  "expected_detection_signals",    # ground truth for detectABILITY
  "behavioral_changes",            # what the attack did, for the UI
  "synthetic_transaction_ids", "victim_cards",
  "ground_truth": "fraud", "synthetic": True,
}
```

**Scheduling.** Campaigns are staggered across the observation window (`phase` rotates the
schedule). Without this, each vector occupies one point in time and a temporal split
silently becomes a held-out-attack-type experiment — a different and much harder question.
`evaluate.py` runs three rotated waves so the standard evaluation is fair, then measures
the harder question deliberately in `zero_day_experiment`.

**Identity uniqueness.** Each campaign carries a per-campaign uid in its transaction ids.
Without it, two campaigns of the same vector both start counting at 1 and collide, silently
corrupting any join between the stream and its scores. A regression test guards this.

## 5. Feature layer (`features.py`)

57 features, all strictly causal. Window statistics use `searchsorted` over sorted
timestamps and exclude the current row; running moments come from shifted cumulative sums.
There is no whole-column aggregate, no target encoding, and no future information anywhere.

Families, chosen from what the evidence supports:

| Family | Examples | Why |
|---|---|---|
| Multi-horizon velocity | `card_txn_1h/24h/7d`, `card_amt_24h` | The workhorse of production systems |
| Deviation from the entity's **own** baseline | `card_amt_z`, `card_amt_ratio`, `card_cadence_std` | The only way to catch ATO and scams, where credentials are genuine |
| Neighbour aggregation | `dev_prior_cards`, `ip_prior_cards`, `mch_prior_cards` | GADBench found this beats bespoke GNNs when fed to a tree ensemble |
| Verification / exemption posture | `threeds_authenticated`, `sca_low_value`, `band_proximity` | Where payments realism lives |

`band_proximity` deserves a note: it measures how far below the nearest PSD2 exemption
threshold an amount sits. Attackers who game banded logic cluster just underneath, so
proximity-from-below is itself a signal.

**Causality is tested, not asserted.** `test_features_are_causal` rebuilds features on a
time-truncated prefix and requires exact equality with the full run.

## 6. Detection layer (`detect.py`)

```
transaction
    │
    ├─► Stage 1  RULES        39 named signals over causal features       ~always
    │            cheap, auditable, instantly deployable
    │
    ├─► Stage 2  MODEL        HistGradientBoostingClassifier              ~always
    │            57 features, class-weighted (never resampled)
    │
    ├─► Stage 3  GRAPH        connected components over shared            top 20%
    │            device / network / beneficiary structure
    │
    └─► ARBITER  logistic regression over component log-odds
                 → isotonic calibration → risk score → band → action
```

**Why a cascade.** Rules are what fraud teams actually trust and can deploy in hours; the
model catches what rules miss; the graph stage is expensive and only earns its cost on
traffic that already looks suspicious. Gating is by **explicit compute budget** (top 20%),
not an absolute score threshold — a fixed threshold drifts with the score distribution and
degenerates into "run everything".

**Why an arbiter.** A logistic regression over five component scores is small, transparent,
and its coefficients are exact — which is what makes the explanation additive and true by
construction rather than estimated.

**Why three temporal slices.** The model is fit on the first 60%, the arbiter on the next
20%, the calibrator on the final 20%. The arbiter never sees the model's training data and
the calibrator never sees the arbiter's, so neither inherits optimism.

Risk bands: `≥0.85 CRITICAL → BLOCK`, `≥0.60 HIGH → STEP_UP`, `≥0.30 MEDIUM → REVIEW`,
else `LOW → ALLOW`.

## 7. Explainability (`explain.py`)

The arbiter's log-odds decompose exactly:

```
logit(risk) = intercept
            + w₁·logit(p_model) + w₂·s_rules + w₃·s_graph
            + w₄·ring_flag + w₅·injection_flag
```

Every term is `coefficient × value` — verified against `arbiter.decision_function()` in
both the module self-check and the test suite.

**What we do not claim.** TreeSHAP was unavailable in this environment (`shap` needs
`numba`, which fails to build on Python 3.14; `lightgbm` needs an OpenMP runtime we cannot
install). Rather than substitute an approximate explainer and present it as attribution,
per-row attribution *inside* the gradient-boosted component is explicitly not claimed. Its
contribution appears as one exact term, and its feature importance is reported globally via
permutation importance and labelled as global. That caveat travels with every explanation
payload, and a test asserts it is present.

## 8. Service layer (`api.py`)

FastAPI. Endpoints: `/api/health`, `/api/taxonomy`, `/api/environment/boot`,
`/api/environment`, `/api/attack/launch`, `/api/campaigns`, `/api/transactions`,
`/api/transactions/{id}/explain`, `/api/graph`, `/api/metrics`, `/api/model/importance`,
`/api/rules`, `/api/audit`, and `WS /ws/stream`.

- **No outbound network client.** The service imports no HTTP library and holds no
  credentials. Verified by AST inspection in the test suite.
- **Audit trail** in SQLite (stdlib) — append-only record of environment changes,
  simulated campaigns and analyst actions.
- **Graph pruning.** `/api/graph` returns only the subgraph induced by *shared*
  infrastructure (entities touching 2+ distinct cards). An unpruned graph is mostly
  singleton card→merchant pairs, which renders as noise and hides ring structure entirely.

## 9. Frontend (`frontend/`)

Seven panels: Overview · Red Team · Live Stream · Investigate · Fraud Network ·
Performance · Audit Trail.

Design decisions worth defending:

- **Dark-primary** — ops consoles are used in low light for long sessions. Not pure black
  (OLED smear, and it destroys elevation cues).
- **Colour never carries meaning alone** — every status colour is paired with a text label.
- **Tabular figures** for all numeric columns, preventing the width jitter that makes dense
  tables look amateurish.
- **Focus rings preserved**, `prefers-reduced-motion` respected, motion 150–300 ms with
  ease-out on enter and no overshoot on data rows.
- **Hand-rolled force-directed graph** (~30 lines) instead of a graph library: no extra
  dependency or licence surface, and a fixed iteration count keeps the layout stable across
  reloads — which matters when a judge views the same screen twice.

## 10. Technology choices

| Choice | Reason |
|---|---|
| Python 3.14 + FastAPI | ML ecosystem; FastAPI gives typed contracts and WebSocket in one dependency |
| scikit-learn `HistGradientBoostingClassifier` | LightGBM-class algorithm without the OpenMP dependency that blocked us |
| NetworkX | Connected components and community detection; BSD-licensed, no build step |
| SQLite (stdlib) | Audit trail needs durability, not a server |
| React 19 + Vite + Tailwind v4 | Fast builds, no config sprawl, standard vocabulary |
| Recharts | Declarative charts over an SVG renderer; adequate for this density |
| **No** Redis / Postgres / Docker / queue | Nothing in the demo path needs them. Every added service is a way for a live demo to fail |

All dependencies are OSI-permissive (BSD-3-Clause / MIT / Apache-2.0), as Kaggle
Foundational Rules §6c requires. `SDV`/`CTGAN` were excluded on licence grounds (Business
Source Licence, not OSI-approved) despite being technically attractive.

## 11. Scaling path

Honest about what this prototype is and what production would require:

| Concern | Today | Production |
|---|---|---|
| Feature computation | Batch recompute (0.10 ms/row amortised) | Streaming feature store with incremental windowed aggregates |
| Decision latency | p50 13.7 ms, p99 18.8 ms in-process | Same shape; model serving behind a thin RPC layer |
| Graph stage | Recomputed per batch on the gated slice | Incrementally maintained entity graph; Grab documents real-time graph updating as the hard part |
| State | In-process DataFrames | Event log + feature store; the cascade itself is stateless |
| Labels | Known by construction | Chargeback/investigator feedback with weeks of delay — the delay block in evaluation models this |

The cascade shape is the part that transfers directly: cheap deterministic checks on all
traffic, a model on all traffic, expensive relational analysis on a budgeted slice.
