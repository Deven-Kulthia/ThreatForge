# Design Decisions

Decision log. Each entry states the choice, the reason, and — where relevant — what we gave
up. Several are decisions *not* to build something, which are the ones most worth recording.

---

## D1 — Closed loop, not a pipeline

**Decision.** Attacks train the defence, and defensive gaps are measured per-vector and
per-signal so they can generate new attacks.

**Why.** The challenge brief states it twice: *"The best solutions turn their own simulated
attacks into the training ground for a stronger defense"* and *"the gaps your defense
reveals feed back into new attack ideas."* A submission that is 90% detector and 10%
generator misses half the stated brief.

**Consequence.** The generator is a scored deliverable, not scaffolding — it feeds the
detector, the metrics, and the demo simultaneously.

---

## D2 — Generate our own data; use no public dataset

**Decision.** 100% self-generated synthetic data.

**Why.** The competition supplies none, and generating gives exact ground truth for every
attack: which transactions are fraudulent, which campaign they belong to, which signals
*should* fire, and how strong the attack was. That is what makes per-signal recall possible.

**Also.** `SDV` and `CTGAN` were excluded on licence grounds — Business Source Licence, not
OSI-approved, which conflicts with Kaggle Foundational Rules §6c. IEEE-CIS was excluded
because it contains real (masked) transactions and is rules-gated.

**Risk we accepted and mitigated.** Synthetic fraud can be trivially separable, which would
make any score meaningless. Mitigations: legitimate and adversarial traffic come from
independent code paths; 12 of 25 vectors are deliberately designed to overlap legitimate
behaviour; per-attack recall is reported worst-first so the hard cases are visible.

---

## D3 — No graph neural network

**Decision.** Connected components and Louvain over shared device/network/beneficiary
edges, with neighbour-aggregated features fed to the tree ensemble. No GNN.

**Why.** GADBench (NeurIPS 2023, 29 models, 10 datasets to ~6M nodes) found that *"tree
ensembles with simple neighborhood aggregation can outperform the latest GNNs tailored for
the GAD task."* "GAD in the Wild" found most GNNs collapse toward **zero recall** at
million-scale with 0.1% anomaly rates. Grab, who deploy graph methods in production,
document real-time graph serving as unsolved.

**What we gave up.** Representation learning over the graph. The evidence says we would
likely have lost to our own tabular baseline while spending days and being unable to defend
the latency.

**How this reads to a judge.** "We evaluated GNNs against the published benchmark and chose
the approach the benchmark endorses" is stronger than either building one uncritically or
omitting graphs entirely.

---

## D4 — No SMOTE; class weighting instead

**Decision.** `class_weight="balanced"`. No resampling of any kind.

**Why.** Three converging findings: a systematic evaluation concludes *"RUS and SMOTE
consistently degraded performance and are therefore not recommended"*; SMOTE's
within-class-homogeneity assumption breaks when the minority class is multimodal — and
fraud is definitionally multimodal, being many distinct typologies; and applying SMOTE
before the train/test split is a documented leakage source that explains most of the
99.9%-accuracy fraud papers in circulation.

**Bonus.** Nearly every hackathon fraud project uses SMOTE, and many use it wrong. Stating
this rejection with citations is the cheapest credibility in the project.

---

## D5 — Calibration is mandatory

**Decision.** Isotonic regression on a held-out temporal slice. Report Brier and ECE with a
reliability diagram.

**Why.** Random undersampling can drive ECE from 0.008 to 0.395 at imbalance ratio 70.
Without calibration, a threshold like "block above 0.9" has no defensible meaning. With it,
0.9 really does mean roughly a 1-in-10 false-block rate, which is what makes a cost-based
threshold arguable to a risk owner.

**Measured.** ECE 0.0038, Brier 0.0045.

---

## D6 — Temporal splits with a delay block

**Decision.** Train on the earliest 65%, discard the next 5% of the timeline, test on the
remainder.

**Why.** Random splits train on events occurring after the ones being scored. The discarded
block models an operational fact: chargeback and investigator labels arrive weeks late, so
a model deployed today cannot have been trained on last week's still-unlabelled fraud.

**Consequence.** Our headline PR-AUC (0.944) is lower than the in-sample figure (0.935–0.99
depending on configuration) would suggest, and that is the point.

---

## D7 — Cascade gated by compute budget, not score threshold

**Decision.** The graph stage runs on the top 20% of traffic by pre-score.

**Why.** An absolute threshold drifts with the score distribution. Our first implementation
used `≥0.15` and silently degenerated into running the expensive stage on 100% of traffic.
A fixed budget is also how production cascades are actually specified — capacity, not
score.

---

## D8 — Explainability by architecture, not by post-hoc estimator

**Decision.** The final score is produced by a logistic arbiter over five component scores,
so its log-odds decompose exactly. Per-row attribution inside the gradient-boosted
component is explicitly not claimed.

**Why.** TreeSHAP was unavailable (`shap` requires `numba`, which fails to build on Python
3.14; `lightgbm` requires an OpenMP runtime unavailable without Homebrew). The options were
(a) an approximate explainer presented as attribution, or (b) an architecture whose
explanation is true by construction. We chose (b).

**Supporting evidence.** Across 3,735 real analyst case reviews, standard XAI metrics were
found *decoupled* from human-perceived clarity, and explanations raised analyst confidence
without raising accuracy — a documented automation-bias risk. Attention-as-explanation is
contested in the literature, so attention weights are never shipped as reason codes.

---

## D9 — LLM off the critical path

**Decision.** No LLM makes a block decision. No LLM is our evaluator. Any LLM use is
narration only, and the system runs fully offline without one.

**Why.** LLM-agent triage has been measured *underperforming* plain thresholding (65.0% vs
71.7%); an XGBoost session detector runs ~9× faster than LLM detectors; LLM serving P99 is
6.4–8.7 s even after optimisation, which is orders of magnitude outside an authorization
budget. LLM-as-judge is separately unreliable, with identity-aware bias up to +7 points.

**What we do instead.** Demonstrate a prompt-injection **defence**: adversarial text in
merchant-controlled fields is treated as untrusted data, never concatenated into a prompt,
and shown being contained (OWASP LLM01:2025).

---

## D10 — Feasible-action attacks

**Decision.** Attacks may only manipulate what an attacker genuinely controls: amount,
timing, cadence, merchant/MCC, channel, device, IP, user agent, card choice, sequencing.

**Why.** The literature's standing criticism of tabular adversarial work is that it
perturbs infeasible features — you cannot set `amount = 43.7291`. *Attack realism, not
attack success, is the open problem.* This maps directly onto the challenge's "fidelity of
attacks in simulation" criterion.

**Exception, deliberately.** Where the real attack path produces a verification outcome, we
model it: OTP interception legitimately yields 3-D Secure `AUTHENTICATED`. Refusing to model
that would make the hardest real attack invisible.

---

## D11 — Public repository named after the team *(reversed on 31 Aug 2026)*

**Decision.** Public GitHub repo named `ThreatForge`, matching the Kaggle team name.

**Originally decided.** Private repo, publish after results on 5 Sep 2026. The reasoning was
that Kaggle Foundational §6a prohibits private code sharing during the competition period,
and §6b permits public sharing only on Kaggle's own forums — where it is then deemed
OSI-licensed to every competitor. A private repo linked from the writeup appeared to avoid
both hazards.

**Why it changed.** The competition host published Official Submission Guidelines requiring
a **public** repository **named after the team** (Step 4), and confirmed in the discussion
thread that GitHub specifically is required. An explicit instruction from the organiser
resolves the §6a/§6b ambiguity that the private-by-default reading was hedging against:
disclosure on terms the organiser mandates is not the private side-channel §6a targets.

**What we did before flipping visibility.** Audited the full git history for credentials —
`.env` was never committed, and no token, key or secret appears in any commit. Confirmed the
captured Kaggle pages are untracked, so none of the organiser's page content is republished.

**Cost of the reversal.** Our work is now visible to other entrants before judging. That is
unavoidable given the requirement, and it is symmetric — every entrant is held to it.

---

## D12 — No Redis, Postgres, Docker, queue or orchestration

**Decision.** SQLite (stdlib) for audit; in-process state for everything else.

**Why.** Nothing in the demo path needs them, and every added service is another way for a
live demo to fail in front of judges. `docs/architecture.md` §11 states honestly what
production would require instead.

---

## D13 — Taxonomy documentation generated from code

**Decision.** `docs/fraud-taxonomy.md` is generated by `scripts/gen_docs.py` from
`attacks.py`.

**Why.** A hand-maintained parallel table guarantees drift. Generation makes the code the
single source of truth and lets a reviewer verify agreement by re-running one command.

---

## D14 — Competition constraints as executable tests

**Decision.** `backend/tests/test_security.py` parses the simulator modules with `ast` to
prove they import no network, subprocess or dynamic-execution capability; asserts no
identifier resembles or Luhn-validates as a PAN; asserts every record is flagged synthetic
with no code path able to unset it.

**Why.** Rules §3(b) requires that adversarial testing cannot target live systems. A README
promise is unverifiable; a failing build is not. This converts compliance from an assertion
into a property.

---

## D15 — Report what we do not do

**Decision.** `UNIMPLEMENTED_SIGNALS` names the five signals we cannot emit and why, and
`evaluate.py` surfaces them in the metrics artifact and generated report.

**Why.** Five of the taxonomy's 47 declared signals require data outside an authorization
message — dispute lifecycle, session telemetry. Silently omitting them would make
per-signal recall look like a mysterious miss. Naming them turns a gap into a scoping
statement, and it is the difference between a report and a sales pitch.

---

## Revisions

Decisions that changed during the build, recorded because the reasoning matters:

| Change | Trigger |
|---|---|
| Attack scheduling: appended → staggered across the window | Temporal split had zero positives in early slices, making the detector untrainable |
| Latency: single figure → decision cost vs feature-build cost | The original measurement timed a full batch feature rebuild per call, reporting a misleading 285 ms |
| Graph endpoint: all entities → shared-infrastructure subgraph only | 688 nodes rendered as noise; ring structure was invisible |
| Alert chart: all four bands → three actionable bands | LOW (33k) flattened MEDIUM/HIGH/CRITICAL into invisibility |
| Positioning: "novel category" → "extends Mastercard's own published direction" | Research found Mastercard ships Threat Scan and AI Garage has published in this exact area |
