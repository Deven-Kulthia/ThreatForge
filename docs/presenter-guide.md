# Presenter's Guide

Everything you need to run, test, present and defend Aegis. The 7-minute demo script itself
lives in `docs/demo-flow.md` — this document covers everything around it: the framing at
three lengths, the exact commands, and the question bank.

---

## Part 1 — What you built, in three lengths

### 30 seconds (an elevator, a judge walking past)

> "GenAI made fraud cheap to *invent*, but fraud models can only learn from fraud that already
> happened — chargeback labels arrive weeks late. Aegis flips that: it generates 25 GenAI-era
> attack vectors, uses them to train and stress-test the defence, and grades detection per-signal
> so we know exactly what the defence is blind to. Those blind spots become the next attack.
> It's a closed loop, and every number reproduces from a clean checkout."

### 2 minutes (the standard pitch)

Add, in this order:

1. **The gap.** Supervised fraud detection needs labelled examples. A novel typology is
   out-of-distribution by definition. You cannot classify your way out of that — you have to
   manufacture the unseen fraud.
2. **Identify.** 25 vectors, 10 categories, each mapped to MITRE ATLAS, each naming the specific
   role generative AI plays. 12 are deliberately built to overlap legitimate behaviour.
3. **Generate.** Agents that may only move what a real attacker controls — amount, timing,
   cadence, merchant, device, sequencing. Never the victim's own history or issuer-side state.
4. **Defend.** Three-stage cascade — 39 rules, gradient boosting, graph structure on the riskiest
   20% — with exact additive reason codes. PR-AUC 0.944, p99 18.8 ms inline.
5. **The loop.** Attacks declare their expected signals *before* running, so a miss is
   attributable. 39 of 39 declared signals implemented; the 8 we can't do are named with reasons.

### 10 minutes

Run the live demo in `docs/demo-flow.md`. Do not narrate architecture at a judge — show the
screens and let the system make the argument.

---

## Part 2 — How to run it

### First time, from a clean checkout

```bash
cd "/Users/devenkulthia/Mastercard Hackathon"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd frontend && npm install && cd ..
.venv/bin/python -m backend.app.evaluate     # regenerates artifacts/metrics.json (~3 min)
```

### Every time you demo (two terminals)

```bash
# terminal 1 — backend
.venv/bin/uvicorn backend.app.api:app --port 8000

# terminal 2 — dashboard
cd frontend && npm run dev
```

Then open **http://localhost:5173** and click **Start environment** (boots in 5–15 s).

### Confirm it's alive before you present

```bash
curl -s localhost:8000/api/health     # -> {"status":"ok", ...}
curl -s -o /dev/null -w "%{http_code}\n" localhost:5173    # -> 200
```

### Rebuild the deck (only if metrics change)

```bash
.venv/bin/python scripts/make_deck.py     # -> artifacts/aegis-walkthrough.pptx
```

The deck reads `artifacts/metrics.json`. Re-run `evaluate.py` first if you changed the model, or
the slides and the code will disagree.

---

## Part 3 — How to test it

### The one command that checks everything

```bash
./scripts/verify.sh --full
```

Runs, in order: 6 module self-checks → 113 pytest tests → secrets/compliance scan → metrics
artifact check → TypeScript typecheck → Vite build → Playwright browser smoke test.

**Important:** the browser smoke test is *skipped* unless both servers are already running. Start
them first (Part 2) or you get a false green on the demo path.

### Narrower checks while working

```bash
.venv/bin/python -m pytest backend/tests -q              # 113 tests, ~30 s
.venv/bin/python -m pytest backend/tests/test_detect.py -q   # one suite
.venv/bin/python -m backend.app.detect                   # module self-check
.venv/bin/python -m backend.app.evaluate                 # full metrics regen
cd frontend && npx tsc --noEmit                          # typecheck only
```

### What the 4 test suites actually protect

| Suite | Guards against |
|---|---|
| Data pipeline | Schema drift, duplicate transaction IDs, label leakage into features |
| Detection | Cascade regression, calibration drift, explainer/model disagreement |
| **Security** | Network egress in the simulator (**AST-level**), real-PII patterns, secrets |
| API | Endpoint contracts, WebSocket lifecycle, audit-trail append-only behaviour |

The security suite is the one that matters for rules compliance — it proves the simulator
*cannot* reach a network target rather than asserting it in prose.

---

## Part 4 — Presenting to judges

### The three beats that win this

1. **Show the loop, don't describe it.** Launch an attack live in Attack Simulator, then show the signal
   attribution — which declared signals fired and which missed. The misses are the loop's output.
2. **Volunteer a weakness before they find it.** Go to the worst-first per-attack table yourself.
   Judges trust a presenter who shows the failures; they discount one who only shows wins.
3. **Say "every number regenerates from a clean checkout."** Then offer to run
   `./scripts/verify.sh --full` in front of them. Almost nobody can do this.

### Sequence (7 min) — full script in `docs/demo-flow.md`

| Time | Screen | The one thing to land |
|---|---|---|
| 0:00 | Boot | Everything is synthetic; card identifiers are tokens |
| 0:45 | Overview | PR-AUC with a bootstrapped CI, not accuracy |
| 1:45 | **Attack Simulator** ⭐ | Expected signals declared *before* launch |
| 3:45 | Live Stream | The queue an analyst would actually work |
| 4:30 | Investigate | Exact decomposition + the honest global-importance caveat |
| 5:45 | Fraud Network | One device, 31 cards — invisible per transaction |
| 6:30 | Performance | Temporal split with delay block; worst-first recall |
| 7:15 | Close | Loop · feasible attacks · honest numbers |

### Delivery notes

- **Slow down on Attack Simulator.** It's the half of the brief most entrants skip, and it's where your
  differentiation is. Two minutes minimum.
- **Never say "accuracy."** At 2.98% prevalence it's meaningless and a payments judge will mark
  you down for using it.
- **If the live demo breaks**, switch to `artifacts/screenshots/` immediately without apologising
  twice. Eight real full-page captures. Say: "these are real captures of this system, not mockups."
- **Have the deck open in a second window** as the fallback-of-the-fallback.

---

## Part 5 — The question bank

### A. Detection / ML

**"PR-AUC 0.944 seems too good. Is your synthetic fraud just trivially separable?"**
> The honest answer is that it would be, if we let the generators cheat. They can only move what an
> attacker controls — amount, timing, cadence, merchant, device, sequencing. They cannot touch the
> victim's baseline, issuer risk state, or AVS/CVV results. And 12 of 25 vectors are deliberately
> built to overlap legitimate behaviour. The proof it isn't trivial: adaptive mimicry sits at 0.015
> recall and SIM-swap OTP at 0.042 within a 1% review budget. If the data were trivially separable
> those would be 1.0.

**"Prove your synthetic data is realistic. Don't just tell me it is."**
> `backend/app/fidelity.py`, and the results are in `metrics.json`. Two halves. First, nine
> generated marginals against published reference bands — all nine in band, including Benford MAD
> of 0.0010 on amount leading digits, which is inside Nigrini's "close conformity" threshold of
> 0.006. We didn't tune for that. Second, and more important: univariate AUC on **raw**
> authorization fields. Max is 0.896, and `amount` is only 0.559 with 0.86 overlap — meaning we do
> *not* do "fraud = big transactions," which is the shortcut that makes most synthetic fraud
> corpora trivially separable. No single raw field gives the attacks away.

**"Isn't cross_border at 0.896 AUC a giveaway?"**
> It's the highest single field, and it's realistic rather than an artefact — cross-border
> genuinely carries materially elevated fraud rates in live portfolios. If our cross-border fraud
> rate matched domestic, *that* would be the fidelity failure.

**"Why PR-AUC and not accuracy or ROC-AUC?"**> At 2.98% test prevalence, blocking nothing scores 97% accuracy. ROC-AUC is optimistic under
> imbalance because the true-negative pool is enormous — that's why we report it as 0.989 but
> label it "for comparability only." PR-AUC is the honest summary, and the 95% interval
> (0.931–0.957) is bootstrapped.

**"Why does REFUND_ABUSE_COLLUSION show 0.000 recall? That looks broken."**
> That's a queue-capacity number, not a model number. At a 1% alert budget and 2.98% prevalence,
> the maximum recall *any* detector could achieve is 0.336 — we hit 0.334, which is 99.4% of the
> mathematical ceiling. Those rows lose the competition for 271 review slots. Size the budget to
> prevalence instead and overall recall is 0.909 at 0.909 precision. And look at the mean-risk
> column — the model does rank them highly.

**"How do you know you're not leaking labels or the future?"**
> Three defences. Temporal split with a 5% delay block discarded between train and test, because
> chargeback labels arrive weeks late and a random split leaks the future. All 57 features are
> strictly causal — computed only from data available at authorization time. And the test suite
> verifies causality on a prefix: recomputing features on a truncated history must give identical
> values.

**"Why no deep learning / GNN?"**
> GADBench showed trees plus neighbour aggregation outperform purpose-built GNNs on tabular graph
> anomaly detection. We get the graph signal from an explicit graph stage instead, which is also
> explainable and cheap enough to sit inline. A GNN would have cost latency and explainability for
> no measured accuracy gain.

**"Why isotonic calibration?"**
> Because a risk score is only useful to a downstream policy if 0.9 means 0.9. Isotonic on a
> held-out temporal slice gets ECE to 0.0038, which lets a bank set thresholds on expected loss
> rather than an arbitrary cut. Platt scaling assumes a sigmoid shape our cascade doesn't have.

**"Where's SHAP?"**
> Couldn't install it — libomp and numba are unavailable on Python 3.14 in this environment.
> Rather than ship an approximate explainer and call it attribution, we made the arbiter additive
> so its decomposition is exact arithmetic, verified against the model's decision function in the
> test suite. The boosted component's importance is reported globally and *labelled* as global. We
> don't claim per-row attribution we can't compute.

### B. Payments domain

**"Your 3.83% fraud rate is nothing like a real portfolio."**
> Correct, and we say so in the deck. Live card portfolios run roughly 0.1–1%; PSD2 RTS reference
> bands are 1–13 bps. We need 3.83% to train and evaluate 25 distinct vectors on a synthetic
> corpus. The consequence is that threshold-dependent figures — precision, alert-rate recall,
> insult rate — would shift in production. PR-AUC, calibration and latency are the transferable
> ones.

**"Could this actually sit in an authorization flow?"**
> p99 is 18.8 ms for the inline decision path with features supplied. The design choice that makes
> it hold: the expensive graph stage runs on the riskiest 20% of traffic as an explicit *compute
> budget*, not a score threshold. A threshold lets cost spike exactly when an attack floods the
> high-risk band; a budget cannot.

**"What's your false-positive story? Declining good customers is expensive."**
> Insult rate 0.0008 at the best-F1 point — 8 false positives against 26,251 legitimate payments.
> We also report operating points against analyst review capacity rather than only at best-F1,
> because a queue nobody can work isn't a control.

**"Is the schema realistic?"**
> ISO-8583-inspired authorization fields — 3-D Secure status, AVS result, SCA exemption claimed,
> MCC, POS entry mode, cross-border corridor. That matters because it constrains what features can
> exist: anything needing dispute-lifecycle or session telemetry we *cannot* build, and we list
> those 5 signals explicitly rather than pretending.

**"You have no PANs anywhere?"**
> None. Card identifiers are tokens by construction — a PAN never exists in the system, synthetic
> or otherwise. Every record carries `synthetic: true` and the UI labels it in the header.

### C. Novelty / the loop

**"Isn't this just a simulator plus a classifier?"**
> The return path is what makes it different. Every attack declares its expected detection signals
> *before* it runs, so we grade per-signal rather than per-transaction. That converts "we caught
> 88%" into "here are the specific mechanisms we're blind to" — which is the specification for the
> next round of attacks. 39 of 39 declared signals are implemented and the 8 we can't do are named
> with reasons.

**"How is this different from what Mastercard already has?"**
> It extends the same direction rather than competing with it. Threat Scan simulates *known*
> attacks against issuers; AI Garage has published on adversarial fraud generation. Aegis generates
> *novel* attacks instead of replaying known ones, constrains them to feasible actions, and wires
> them into a continuous per-signal-graded loop. That framing is deliberate — it makes this
> adoptable rather than speculative.

**"Prove it generalises to attacks you didn't train on."**
> Six vectors held out of training entirely, scored at a threshold calibrated on seen traffic only —
> no retuning. Aggregate unseen recall 0.718 on 975 transactions. BIN enumeration 1.000, synthetic-ID
> bust-out 0.982, credential stuffing 0.974, APP scam 0.800, romance fraud 0.500. Agent
> impersonation is the weak one at 0.116.

**"Why is agent impersonation so bad?"**
> Because in an authorization message a legitimate agentic purchase and an impersonated one are
> nearly identical. Separating them needs agent-identity attestation the schema doesn't carry yet.
> That's a roadmap item and I'd rather name it than paper over it — it's also exactly the kind of
> gap the loop is designed to surface.

### D. Commercial / scale

**"Who buys this, and how does it fit an existing stack?"**
> It sits beside an issuer's or PSP's existing fraud stack as a red-team and evaluation harness —
> the loop stress-tests controls the bank already owns, and per-signal grading tells them which of
> their own rules are blind. It doesn't ask them to replace a scoring engine.

**"Does it scale?"**
> Scoring is stateless behind FastAPI, so horizontal scale is the only axis needed. Feature build
> is 0.10 ms/row batched and would be incremental in production rather than recomputed. No GPU
> anywhere, no external service on the decision path.

**"Where's the LLM?"**
> Deliberately off the critical path. It narrates and helps author attack scenarios; it never makes
> the block decision. A hosted model in an authorization path is a latency and availability risk,
> and a non-deterministic decision is not auditable.

### E. Compliance (know these cold)

| Question | Answer |
|---|---|
| Real data anywhere? | No. 100% self-generated synthetic. No cardholder data, PII or production data (Rules §3a). |
| Can the simulator hit a live system? | No — it has no network client, enforced by an AST test in the security suite (Rules §3b). |
| Dependency licences? | All OSI-permissive. 41 Python + 121 npm packages audited: zero AGPL/GPL/SSPL. (Foundational §6c) |
| Why is the repo public? | The host's submission guidelines (Step 4) require a public repo named after the team. That instruction supersedes our earlier private-by-default reading of Foundational §6a. |
| Who owns the IP? | We do. Rules §5 — Mastercard gets a purpose-limited licence for judging and promotion. |

### F. Hostile / trap questions

**"Did an AI write this?"**
> Yes, with me directing it — and everything in it is verified rather than asserted. That's the
> part I'd point at: 113 tests, a one-command verification gate, and a deck generated from the
> metrics file so no number is hand-typed. I can regenerate every figure in front of you.

**"What's the weakest part of the project?"**
> Adaptive mimicry detection, at 0.015 recall within a 1% budget. It learns the victim's own
> baseline and stays inside it, which defeats deviation-based features by construction. Beating it
> probably needs sequence modelling over the account's full history rather than windowed
> aggregates. Second weakest is agent impersonation at 0.116 zero-day recall, for schema reasons.

**"What would you do with another month?"**
> Those two rows first. Then agent-identity attestation in the schema, and a second-order loop
> where the attack generator itself trains against the current detector rather than being
> hand-parameterised.

**"Why should we believe your numbers?"**
> Don't believe them — reproduce them. `pip install -r requirements.txt`, then
> `python -m backend.app.evaluate`, then `./scripts/verify.sh --full`. Three commands from a clean
> checkout and every figure in the deck regenerates.

---

## Part 6 — Numbers to have memorised

**Headline:** PR-AUC **0.944** (CI 0.931–0.957) · F1 **0.929** (P 0.972 / R 0.891) ·
p99 **18.8 ms** · zero-day **0.718**

**Scale:** 25 vectors · 10 categories · 90,258 transactions · 3.83% fraud · 1,650 cards ·
263 merchants · 44 days · 75 campaigns

**Defence:** 39 rules · 57 causal features · graph on top 20% · ECE 0.0038 · VDR 0.941

**The one that saves you:** 1% budget recall 0.334 against a **ceiling of 0.336** — 99.7% of the
maximum achievable. Prevalence-matched alternative: **0.909 recall at 0.909 precision**.

**Quality:** 113 tests · one-command gate · 41 Python + 121 npm deps, zero copyleft

---

## Part 7 — Pre-demo checklist

Run this 10 minutes before presenting:

```bash
cd "/Users/devenkulthia/Mastercard Hackathon"
.venv/bin/uvicorn backend.app.api:app --port 8000 &
(cd frontend && npm run dev) &
sleep 12
curl -s localhost:8000/api/health
./scripts/verify.sh --full          # must say VERIFIED, with browser smoke GREEN not skipped
```

- [ ] Both servers up, health returns `ok`
- [ ] Browser open at localhost:5173, environment **already booted** (don't make judges watch a boot)
- [ ] `artifacts/screenshots/` open in a second window as fallback
- [ ] `artifacts/aegis-walkthrough.pptx` open as fallback-of-fallback
- [ ] Laptop on mains, notifications off, screen-share tested
- [ ] You can say the ceiling answer (0.334 vs 0.336) without looking it up

---

## Part 8 — Known failure modes and recovery

| Symptom | Cause | Fix |
|---|---|---|
| Boot screen never appears | Backend down | `curl localhost:8000/api/health` |
| "Environment not initialised" | Not booted | Click **Start environment**, wait 15 s |
| Performance panel empty | No metrics artifact | `.venv/bin/python -m backend.app.evaluate` |
| Live stream static | Replay is finite (last 600 txns) | Switch tabs and back |
| Graph looks like noise | Risk filter too high | Lower **min risk**, or launch `MULE_FANOUT` |
| Browser smoke "skipped" | Servers weren't running | Start both, re-run the gate |
| Deck numbers ≠ UI numbers | Metrics regenerated after deck build | `python scripts/make_deck.py` |
