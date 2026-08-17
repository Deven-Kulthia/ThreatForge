# Aegis — AI Defence Lab for Payment Security

**Mastercard Innovation Challenge 2026 · AI Defence Lab for Payment Security**
Solo entry. 100% synthetic data. Simulator network-isolated by construction.

> **Paste target:** this is the text for the Kaggle **Writeups** submission. Submit a minimum
> version EARLY — Rules §2/§3: *"any un-submitted or draft work by the deadline will not be
> considered."* Then keep updating it.

---

## The three required artifacts

| # | Artifact | Where |
|---|---|---|
| 1 | **Code repository** — runnable, covers all three pillars | `Deven-Kulthia/aegis-ai-defence-lab` (private until judging concludes, per Kaggle Foundational §6a) |
| 2 | **Solution walkthrough** (.pptx) | `artifacts/aegis-walkthrough.pptx` — 14 slides, generated from verified metrics |
| 3 | **Working web prototype** | React command centre, 7 panels; `npm run dev` + `uvicorn`. Fallback captures in `artifacts/screenshots/` |

---

## One-paragraph summary

GenAI made fraud cheap to *invent*, while defences still learn only from fraud that already
happened — chargeback labels arrive weeks late, so a novel typology is out-of-distribution by
definition. Aegis closes that gap by generating the attacks first. It identifies 25 GenAI-era
payment-fraud vectors across 10 categories, simulates them with agents constrained to only the
levers a real attacker controls, and defends with a three-stage cascade that reports honest,
reproducible numbers. Because every generated attack **declares the detection signals it should
trip before it runs**, detection is graded per-signal — so a miss is attributable, and the
defence's blind spots become the specification for the next round of attacks. That return path is
what makes this a loop rather than a pipeline.

---

## Pillar 1 — Identify

**25 distinct attack vectors across 10 categories**, each mapped to MITRE ATLAS, each annotated
with the specific role generative AI plays, and each carrying a `hard_to_detect` flag.

| Category | Representative vectors |
|---|---|
| Synthetic identity | Generated-document application farm, history building, bust-out |
| Deepfake onboarding | Liveness / KYC defeat at account opening |
| Account takeover | Credential stuffing, SIM-swap OTP interception |
| AI-driven scams | APP scam via conversational LLM, romance / pig-butchering |
| Agentic commerce | Agent impersonation, prompt injection via merchant-controlled fields |
| Fraud rings | Coordinated multi-card ring, mule fan-out |
| Merchant abuse | Fake storefronts, refund collusion |
| Adaptive evasion | Velocity evasion, mimicry of the victim's learned baseline |
| Card testing | BIN enumeration bursts |
| Cross-border | Corridor and SCA-exemption abuse |

Coverage includes all four threats Mastercard AI Garage named publicly (synthetic identities,
deepfake KYC, fake merchant storefronts, AI-enabled scams). **12 of 25 vectors are deliberately
built to overlap legitimate behaviour** — the taxonomy is not padded with easy wins.

Full taxonomy: `docs/fraud-taxonomy.md`. Threat model: `docs/threat-model.md`.

---

## Pillar 2 — Generate

**Environment.** ISO-8583-inspired authorization schema. 1,650 tokenised cards, 263 merchants,
44 days of traffic, **90,256 transactions at 3.83% fraud** across 75 campaigns. A PAN never
exists in this system — card identifiers are tokens. Every record carries `synthetic: true`.

**The fidelity constraint that matters.** The standing criticism of adversarial ML on tabular data
is that papers perturb features the attacker cannot touch, which produces impressive numbers and
unusable systems. Our generators may move **only** what an attacker really controls:

- Amount, and how it is split across attempts
- Timing, inter-arrival cadence, burst shape
- Merchant and MCC selection
- Device and channel presentation
- Sequencing — probe, escalate, cash out
- Text in merchant-controlled fields

Held invariant — **not the attacker's to change**: the victim's own historical baseline,
issuer-side risk state, network-assigned identifiers, AVS/CVV results returned by the issuer,
another cardholder's genuine behaviour, and any label the defence later assigns.

This costs headline numbers. It is much easier to score well against attacks that cheat by editing
issuer-side features — but an attack requiring rewrites of the victim's own history is data
corruption, not an attack. The constraint is what makes the detection results mean anything
operationally.

**Ground truth.** Every attack emits `attack_type`, `scenario_id`, `strength`, `severity`,
`expected_signals`, and `hard_to_detect`. `expected_signals` is declared *before* execution — this
is the mechanism that makes per-signal grading possible.

**Safety.** The simulator is architecturally incapable of reaching a network target, and that is
enforced by an AST test in the suite, not merely asserted (Rules §3b).

---

## Pillar 3 — Defend

**Three-stage cascade**, in order: 39 deterministic rule signals → `HistGradientBoostingClassifier`
→ graph structure on the riskiest 20% of traffic → arbiter → isotonic calibration.

57 strictly causal features across four families: velocity, deviation from the account's *own*
baseline, graph, and verification-signal coherence. No feature can see the label or the future.

### Verified results

Temporal split with a **5% delay block** between train and test, because chargeback labels arrive
late and a random split leaks the future. Train 58,666 / test 27,077 at 2.98% test prevalence.

| Metric | Value |
|---|---|
| **PR-AUC** | **0.957** (95% CI 0.946–0.969, bootstrapped) |
| ROC-AUC | 0.996 *(reported for comparability; optimistic under imbalance)* |
| **Best-F1 point** | **F1 0.934** — precision 0.989 / recall 0.885 |
| False-positive / insult rate | **0.0003** (8 FP against 26,261 legitimate) |
| Value detection rate | **0.913** — 91.3% of attempted fraud *value* stopped, not just count |
| Calibration | ECE 0.0019 (10-bin), Brier 0.0035, isotonic on a held-out temporal slice |
| **Decision latency** | **p50 16.6 ms / p95 25.9 ms / p99 31.4 ms** (inline path) |
| **Zero-day recall** | **0.781** on 6 typologies never trained on |

PR-AUC is the headline because at 2.98% prevalence a model that blocks nothing scores 97% accuracy.

### Novelty evidence — zero-day generalisation

Six vectors were removed from training **entirely**, then scored at a threshold calibrated on seen
traffic only (no retuning):

| Held-out vector | n | Recall | Mean risk |
|---|---|---|---|
| BIN_ENUMERATION_BURST | 300 | 1.000 | 1.000 |
| SYNTH_ID_BUSTOUT | 168 | 1.000 | 1.000 |
| ATO_CREDENTIAL_STUFF | 115 | 0.983 | 0.992 |
| APP_SCAM_LLM | 30 | 0.933 | 0.977 |
| ROMANCE_PIG_BUTCHERING | 144 | 0.764 | 0.893 |
| AGENT_IMPERSONATION | 216 | 0.190 | 0.570 |
| **Aggregate** | **973** | **0.781** | — |

Recall on attacks the model trained on measures memorisation; this measures whether a causal
feature layer transfers to fraud that did not exist when the model was fit.

**AGENT_IMPERSONATION at 0.190 is our honest weak point.** In an authorization message, a
legitimate agentic purchase and an impersonated one are nearly indistinguishable; separating them
needs agent-identity attestation the schema does not yet carry.

### Explainability

- **Exact additive decomposition** of the arbiter's log-odds — arithmetic, not estimation, and the
  test suite verifies it reconciles with the model's own decision function.
- Ranked reason codes in analyst language, plus a counterfactual (what would change the outcome).
- SHAP could not be installed (libomp and numba unavailable on Python 3.14). Rather than ship an
  approximate explainer and call it attribution, the arbiter was **designed to be additive so its
  explanation is exact by construction**. The boosted component's importance is reported globally
  and **labelled as global** — we do not claim per-row attribution we cannot compute.

---

## The closed loop — the actual contribution

```
IDENTIFY ──▶ GENERATE ──▶ DEFEND ──┐
    ▲                              │
    └──── per-signal recall ◀───────┘
         (named blind spots become the next attack spec)
```

39 of 39 distinct declared signals are implemented. The **8 that are not are named with reasons**
rather than hidden: five need dispute-lifecycle or session telemetry an authorization message does
not carry; three are emitted by the graph or text-safety stage rather than the rule stage. Naming a
gap is more useful than letting it look mysterious — and each named gap is a queued attack idea.

---

## Where it fails — stated plainly

Per-attack recall at a **1% analyst review budget**:

| Vector | Recall @1% | Mean risk | Hard by design |
|---|---|---|---|
| SIM_SWAP_OTP | 0.000 | — | yes |
| REFUND_ABUSE_COLLUSION | 0.000 | — | no |
| ADAPTIVE_MIMICRY | 0.030 | — | yes |

**Read the ceiling before reading the rows.** At a 1% alert budget and 2.98% prevalence, the
maximum recall *any* detector could reach is **0.335**; we reach 0.334 — **99.7% of the
mathematical ceiling**. A 0.000 row means "did not survive the queue", not "invisible to the
model". Size the budget to prevalence instead and recall is **0.918 at precision 0.918**.

Genuinely under-detected: adaptive mimicry (learns the victim's own baseline and stays inside it)
and SIM-swap OTP. Those two rows are what we would fix first.

**Prevalence caveat.** Synthetic prevalence is 3.83% versus roughly 0.1–1% in live card portfolios
— necessary to train and evaluate 25 vectors, but it means threshold-dependent figures would shift
in production. **PR-AUC, calibration and latency are the transferable ones.**

---

## Real-world feasibility in live payments

| Constraint | Design consequence |
|---|---|
| **Latency budget** | p99 31.4 ms inline. The expensive graph stage runs on the riskiest 20% of traffic — an explicit *compute budget*, not a score threshold. Thresholds let cost spike when an attack floods the high-risk band; a budget cannot. |
| **Review capacity** | Operating points reported against analyst capacity, not only at best-F1. A queue nobody can work is not a control. |
| **Auditability** | Append-only SQLite trail of every environment change, campaign and analyst action. Model governance expects decisions to be reconstructable. |
| **Deployability** | No GPU, no AGPL, no external service on the decision path. The LLM narrates; it never makes the block decision. |
| **Scalability** | Stateless scoring behind FastAPI; feature build is 0.10 ms/row batched and would be incremental in production. Horizontal scaling is the only axis needed. |
| **Commercial fit** | Slots in beside an existing issuer/PSP fraud stack as a red-team + evaluation harness — the loop tests controls a bank already owns. |

**Positioning.** This extends Mastercard's own published direction rather than proposing a new
category: Threat Scan simulates *known* attacks against issuers, and AI Garage has published on
adversarial fraud generation. Aegis generates *novel* attacks instead of replaying known ones,
constrains them to be feasible, and wires them into a continuous, per-signal-graded loop.

---

## Technical quality

- **113 tests passing** across 4 suites: data pipeline, detection, security, API.
- `scripts/verify.sh --full` — module self-checks, tests, compliance scan, TypeScript typecheck,
  frontend build, browser smoke test. One command, green or it does not ship.
- **Every number in this writeup and in the deck is generated from `artifacts/metrics.json`** by
  `backend.app.evaluate`. `scripts/make_deck.py` builds the .pptx from that same file, so the deck
  cannot drift from the code. No figure is hand-typed.
- Reproduce from a clean checkout:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m backend.app.evaluate      # regenerates all metrics (~3 min)
./scripts/verify.sh --full                    # everything green
.venv/bin/uvicorn backend.app.api:app --port 8000   # terminal 1
cd frontend && npm run dev                          # terminal 2
```

---

## Compliance

- **Synthetic data only.** No real cardholder data, PII or production payment data (Rules §3a).
- **Simulator never targets live systems** — network isolation enforced by an AST test (Rules §3b).
- **Dependencies all OSI-approved permissive** (BSD-3-Clause / MIT / Apache-2.0). No AGPL, nothing
  limiting commercial use (Kaggle Foundational §6c). Inventory in `requirements.txt`.
- **Repo private until judging concludes** (Kaggle Foundational §6a).
- Responsible-AI and security posture: `docs/security.md`.

---

## Repository map

```
research/   competition rules (verified), threat landscape, existing solutions, sources
docs/       architecture · decisions · threat-model · fraud-taxonomy · detection-methodology
            evaluation · security · demo-flow · deployment
backend/app/ schema · generator · attacks · features · detect · explain · evaluate · api
backend/tests/ 113 tests
frontend/   React + Vite + Tailwind command centre (7 panels)
scripts/    verify.sh · make_deck.py · gen_docs.py · ui_smoke.py
artifacts/  metrics.json · aegis-walkthrough.pptx · screenshots/ · audit.db
```
