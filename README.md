# Aegis — AI Defence Lab for Payment Security

**A closed-loop adversarial AI system for GenAI-era payment fraud: it invents the attacks, simulates them at scale, and trains its own defence on them.**

Built for the **Mastercard Innovation Challenge 2026** (AI Defence Lab for Payment Security, hosted by Mastercard AI Garage at Global Fintech Fest 2026).

> ⚠️ **All data in this project is synthetic.** No real cardholder data, no real PII, and no production payment data is used anywhere. The attack simulator has no network client and cannot reach any external system by construction. See [Security](#security).

---

## Problem

Generative AI has collapsed the cost of payment fraud. Synthetic identities, deepfake KYC, fabricated merchant storefronts and AI-driven scams are now produced at industrial scale, while defences are still tuned on last year's fraud.

The asymmetry is the whole problem, and a practitioner states it best — attackers *"mutate in milliseconds"* while a fraud team needs *about a week* to ship a rule change ([Sardine](https://www.sardine.ai/blog/AI-agents-for-fraud-operations)).

The evidence base:

| Signal | Figure | Source |
|---|---|---|
| FBI IC3 2025 reported losses | **$20.877B**, +26% YoY | [IC3 2025 Annual Report](https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf) |
| Cyber-enabled share of losses | **85%** ($17.697B) | same |
| Losses with an explicit **AI nexus** | **$893,346,472** across 22,364 complaints | same |
| Projected US GenAI-enabled fraud | **$12.3B (2023) → $40B (2027)**, 32% CAGR | [Deloitte CFS](https://www.deloitte.com/us/en/insights/industry/financial-services/deepfake-banking-fraud-risk-on-the-rise.html) |
| iOS biometric **injection** attacks | **+1,151% YoY** (H2 2025) | [iProov](https://www.iproov.com/blog/deepfake-bank-account-kyc-account-fraud-abn-amro) |

## Solution

Aegis implements the challenge's three pillars as a **single feedback loop** rather than a pipeline:

```
   ┌──────────────► IDENTIFY ──────────────┐
   │        25-vector attack taxonomy      │
   │      (MITRE ATLAS-mapped, GenAI-era)  │
   │                                       ▼
DEFEND ◄───────────────────────────── GENERATE
Cascade detector, calibrated       Feasible-action attack agents
risk score, reason codes           over synthetic payment traffic
   │                                       ▲
   └── defensive gaps become new attacks ──┘
```

The loop is the point: attacks we generate become training and stress-testing data for the defence, and wherever the defence fails, that failure is fed back as a new attack variant.

## Key Innovation

**1. Feasible-action attacks, not L_p noise.**
The standing criticism of adversarial ML on tabular data is that it perturbs features an attacker cannot control — you cannot set `amount = 43.7291`, and you certainly cannot forge an EMV transaction counter. Every Aegis attack is restricted to the attacker's *real* action space: amount, timing, cadence, merchant and MCC selection, channel, device, IP, and sequencing across cards. Issuer-side verification results are never forged unless the real attack path genuinely produces them (an intercepted OTP legitimately yields a 3-D Secure "authenticated" status — which is precisely why it is dangerous).

**2. A generator that can produce provably invisible drift.**
Label-free drift monitoring detects covariate shift reliably but **pure concept drift with unchanged P(X) is structurally invisible** — "exactly zero delta" ([1](https://arxiv.org/abs/2604.15740), [2](https://arxiv.org/abs/2604.17836)). Aegis can synthesise exactly that case. This is the rigorous argument for why an attack generator is *necessary* rather than decorative: standard monitoring cannot see this class of change at all.

**3. Detection is graded per-signal, not just per-transaction.**
Every attack declares the signals a competent detector *ought* to fire on, so we measure whether the defence caught an attack **for the right reason** — not merely whether a score crossed a threshold.

**4. A product gap, honestly scoped.**
A structured review of thirteen vendors (Visa, Featurespace, Feedzai, Sardine, Sift, Forter, Signifyd, Riskified, Unit21, Hawk, Quantexa, Socure, Alloy) found **zero** marketing adversarial testing, red teaming, or synthetic attack generation against the customer's own fraud model. What ships instead is *retrospective replay* — Alloy Backtesting, Hawk Production Sandbox, Unit21 Shadow Mode, Sift Workflow Simulation. Sardine's own documentation concedes the limitation: activity "nobody caught at the time was never investigated or labeled, so the past data understates what you actually missed."

**What Aegis is explicitly not claiming.** Mastercard is ahead of the market here, and we say so:

- **Mastercard Threat Scan** (2019) already *"simulates known fraudulent attacks on issuers and pinpoints authorization security weaknesses."* Aegis is not the first system to simulate attacks against payment defences — Mastercard's own product got there first.
- **Mastercard AI Garage has published in precisely this area**: *Adversarial Fraud Generation for Improved Detection* (ICAIF 2022), *Evolutionary Adversarial Attacks on Payment Systems* (ICMLA), *FraudAmmo: Large Scale Synthetic Transactional Dataset for Payment Fraud Detection* (IJCNN 2023), *Prodem* (proactive model-degradation detection under label delay), and *Improving the Robustness of Financial Models through Identification of the Minimal Vulnerable Feature Set* (ICAIF 2023).
- The closest published proof point for adversarially-generated fraud retraining a defence is **Feedzai Research's "The GANfather"** (ICAIF 2023).

**So the contribution is a delta, not a genesis.** Aegis extends Threat Scan's *known-scenario replay* into **generated, novel, evasion-optimised campaigns constrained to the attacker's feasible action space**, wires the result into a continuous loop, and grades detection **per-signal** rather than per-transaction. That is a defensible increment on a direction Mastercard has already published — a stronger position than pretending the idea is new to them.

## Architecture

```
backend/app/
  schema.py      Payment authorization schema — ISO 8583 (DE18 MCC, DE22 entry mode,
                 DE39 response), EMV, 3-D Secure 2 transStatus, PSD2 SCA exemptions,
                 AVS/CVV codes. Ground-truth fields structurally separated from
                 observable fields so label leakage is impossible, not merely discouraged.
  generator.py   Synthetic population + legitimate traffic. Diurnal/weekly rhythm,
                 per-cardholder habits, MCC-conditioned ticket sizes, device stability.
  attacks.py     25-vector taxonomy + feasible-action attack simulators. Emits full
                 ground truth per campaign.
  features.py    Velocity, behaviour-vs-own-baseline, and graph features.        (in progress)
  detect.py      Cascade: rules → HistGradientBoosting → graph signals → ensemble. (in progress)
  explain.py     Additive reason codes.                                           (in progress)
  evaluate.py    PR-AUC, recall @ fixed alert rate, latency p50/p99, calibration.  (in progress)
  api.py         FastAPI + WebSocket live stream.                                 (in progress)
frontend/        React dashboard — payment-security command centre.               (in progress)
```

### Design decisions worth defending

| Decision | Why |
|---|---|
| **No GNN** | GADBench (NeurIPS 2023, 29 models, 10 datasets) found *"tree ensembles with simple neighborhood aggregation can outperform the latest GNNs tailored for the GAD task"*, and GNNs collapse toward zero recall at production scale/imbalance. We use connected components + Louvain for rings and feed neighbour-aggregated features to the tree ensemble. |
| **No SMOTE** | Systematically shown to degrade performance; its within-class homogeneity assumption breaks when the minority class is multimodal — and fraud is definitionally multimodal. Applying it before the split is a documented leakage source that explains most 99.9%-accuracy fraud papers. We use class weighting. |
| **Calibrated probabilities** | Random undersampling wrecks calibration (ECE 0.008 → 0.395 at imbalance ratio 70). Calibration makes a threshold *mean* something: "block above 0.9 ⇒ expected 1-in-10 false block." |
| **LLM off the critical path** | LLM triage has been shown to *underperform* plain thresholding (65.0% vs 71.7%), and LLM serving P99 is seconds — orders of magnitude outside an authorization budget. LLMs narrate; they never decide. |
| **No external dataset** | The challenge provides none, and generating our own gives exact ground truth for every attack. `SDV`/`CTGAN` were additionally excluded on licence grounds (Business Source Licence, not OSI-approved). |

## Technology Stack

Python 3.14 · FastAPI · scikit-learn · pandas · NumPy · NetworkX · SQLite (stdlib) · React + Vite + TypeScript + Tailwind

All dependencies are OSI-approved permissive licences (BSD-3-Clause / MIT / Apache-2.0), as required by Kaggle Foundational Rules §6c.

## Installation

```bash
git clone <repository-url>
cd aegis-ai-defence-lab

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Environment Variables

Copy `.env.example` to `.env` and fill in values. **`.env` is git-ignored and must never be committed.**

```
GITHUB_USERNAME=<your_github_username>
GITHUB_TOKEN=<your_github_personal_access_token>
GITHUB_OWNER=<your_github_username>
GITHUB_REPOSITORY=aegis-ai-defence-lab
```

No credential is required to run the system — Aegis runs fully offline.

## Running Locally

```bash
.venv/bin/python -m backend.app.generator          # generate synthetic traffic (self-check)
.venv/bin/python -m backend.app.evaluate           # reproduce all reported metrics
.venv/bin/uvicorn backend.app.api:app --reload     # API on :8000
cd frontend && npm install && npm run dev          # dashboard on :5173
```

## Synthetic Data

Every record is synthetic and carries `synthetic: true`. Card identifiers are synthetic
network-style tokens — never PANs — mirroring a real tokenized authorization flow and making
real-card data structurally impossible to represent.

Fraud base rates are anchored to regulator and industry reference points rather than the
inflated rates common in public fraud datasets: the PSD2 RTS Annex reference remote-card fraud
rates are 0.01% / 0.06% / 0.13% for ETV bands €500 / €250 / €100, and Stripe reports fraud at
roughly 1 in 1,000 payments.

## Attack Simulation

25 vectors across channels, rails and social-engineering surfaces, each mapped to MITRE ATLAS /
ATT&CK and annotated with the specific role generative AI plays:

| Category | Vectors |
|---|---|
| Synthetic identity | history build-up · bust-out · generated-document application farm |
| Deepfake / ATO | deepfake KYC onboarding · voice-clone call-centre takeover · credential stuffing · SIM-swap/OTP interception |
| Merchant fraud | fabricated storefront · transaction laundering / MCC misrepresentation · collusive refund abuse |
| Scams | LLM-driven APP scam · romance/pig-butchering escalation · invoice redirection (BEC) |
| Enumeration | micro-amount card testing · BIN enumeration burst |
| Fraud rings | mule fan-out · coordinated multi-card ring |
| **Agentic commerce** | agent impersonation · prompt injection via merchant fields · **mandate replay / scope substitution** |
| **Adaptive evasion** | velocity-threshold evasion · low-value SCA exemption stacking · risk-band gaming · **victim-profile mimicry** |
| First-party | dispute abuse |

Each campaign emits structured ground truth: `attack_type`, `scenario_id`, `attack_strength`,
`severity`, `behavioral_changes`, `expected_detection_signals`, `synthetic_transaction_ids`.

Attacks are modelled purely as **observable behavioural change in a transaction stream** — the
level a defender needs in order to build detection, and nothing lower. This repository contains
no operational instructions for committing fraud.

## Fraud Detection

*In progress.* Cascade architecture: cheap deterministic rules → gradient-boosted ensemble →
graph/network signals on the top-k only. Chosen because a tiered cascade is both the most
defensible production pattern and the one that keeps p99 latency inside an authorization budget.

## Risk Scoring

*In progress.* Calibrated probability → risk band → recommended action, with the contributing
signals attached to every decision.

## Explainability

*In progress.* Exact additive reason codes over a fixed signal taxonomy.

We deliberately engage the counter-evidence here: across 3,735 real analyst case reviews,
standard XAI metrics were **decoupled from human-perceived clarity**, and explanations raised
analyst confidence *without* raising accuracy — a documented automation-bias risk. Aegis
therefore reports explanation *fidelity* separately from analyst confidence, and never ships
attention weights as reason codes.

## Evaluation

*In progress.* Metrics: **PR-AUC** (primary), recall at a fixed alert rate, per-signal recall,
value detection rate, insult rate, latency p50/p95/p99, and calibration (Brier / ECE) with a
reliability diagram. Temporal splits only, with a delay block reflecting the reality that
chargeback and investigator labels arrive late.

A 2026 survey of 49 sources found that among 18 fraud sources, **none reported per-decision
latency, cost, or calibration**. Aegis reports all three.

**No metric in this repository is hand-written.** Every number is produced by
`backend/app/evaluate.py` and is reproducible from a clean checkout.

## Testing

```bash
.venv/bin/python -m pytest backend/tests -q
```

## Security

Security is treated as a first-class requirement, not a section.

- **No real data.** Synthetic only, per competition Rules §3(a).
- **Simulator isolation.** The attack simulator operates exclusively on in-memory synthetic
  DataFrames. It contains no network client, no credential handling and no external target —
  it *cannot* reach a live system. This satisfies Rules §3(b) by construction rather than by promise.
- **No secrets in the repository.** `.env` is git-ignored; only `.env.example` placeholders are committed.
- **Prompt-injection defence is demonstrated, not assumed.** Adversarial text in merchant-controlled
  fields is treated as hostile data (OWASP LLM01:2025) and shown being contained.
- **Defensive review.** Application-level security review covering injection, XSS, SSRF, unsafe
  deserialization, dependency licences and LLM-specific risks. See `docs/security.md`.

## Demo

*In progress.* Judge-facing flow: start the synthetic environment → generate legitimate traffic →
launch a safe simulated attack → watch detection fire → inspect *why* → compare attack strength
against detection performance → replay the scenario.

## Project Structure

```
backend/app/      core system (schema, generator, attacks, detection, scoring, API)
backend/tests/    pytest suite
frontend/         React dashboard
docs/             architecture, decisions, threat model, evaluation, security, demo flow
research/         Phase-1 research with full source provenance
requirements.txt  pinned permissive-licence dependencies
```

## Documentation

| Document | Contents |
|---|---|
| [`research/competition.md`](research/competition.md) | Verified competition rules, criteria and constraints |
| [`research/threat-landscape.md`](research/threat-landscape.md) | 10 GenAI fraud threat categories with cited evidence |
| [`research/existing-solutions.md`](research/existing-solutions.md) | Detection state of the art and where it fails |
| [`research/research-sources.md`](research/research-sources.md) | Full source register |
| [`docs/current-state.md`](docs/current-state.md) | Live build state |

## Team

Solo entry — Deven Kulthia.

## Licence

MIT — see [LICENSE](LICENSE).

---

*Submission for the Mastercard Innovation Challenge 2026. Mastercard trademarks and challenge
materials remain the property of Mastercard; this repository is an independent participant
submission and is not endorsed by Mastercard.*
