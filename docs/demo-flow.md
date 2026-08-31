# Demo Flow

A seven-minute walkthrough that shows the closed loop working. Every screen is live — no
recordings, no mock data.

**Setup:** two terminals, then one browser tab at `http://localhost:5173`.

```bash
# terminal 1 — backend
.venv/bin/uvicorn backend.app.api:app --port 8000

# terminal 2 — dashboard
cd frontend && npm run dev
```

---

## The narrative arc

> GenAI made fraud cheap to invent. Our defences are trained on last year's fraud.
> Aegis closes that gap by inventing the attacks first — then training the defence on them.

---

## 0:00 — Initialise the environment (45s)

**Screen:** boot screen.

Click **Start environment**.

**Say:** "This generates a synthetic payment environment — 700 cardholders, 140 merchants,
30 days of authorization traffic — and then trains the defence on 25 simulated attack
campaigns. The defence is learning from attacks we invented. That's the first turn of the
loop."

**Point out:** the synthetic-data badge in the header. Everything is synthetic; card
identifiers are tokens, never PANs.

Takes 5–15 seconds.

---

## 0:45 — Executive overview (1min)

**Screen:** Overview.

**Say:** "33,000 transactions in scope. The alert bands on the left are calibrated risk —
notice we chart only the three bands that require action, because LOW is 33,000 rows and
would flatten everything else into invisibility."

**Then the right panel — this is the credibility moment:**

- **PR-AUC 0.944** with a 95% confidence interval — "PR-AUC, not accuracy, because at this
  class imbalance accuracy is meaningless. The interval is bootstrapped."
- **Decision p99 31 ms** — "that's the inline authorization path, not batch throughput."
- **Zero-day recall 0.718** — "recall on six attack types the model was never trained on."

**Say:** "Every number here comes from `evaluate.py`. None of it is hand-written, and it
regenerates from a clean checkout."

---

## 1:45 — The red team (2min) ⭐ *the differentiator*

**Screen:** Red Team.

**Say:** "This is the half of the brief most entries skip. 25 attack vectors across 10
categories — synthetic identity, deepfake KYC, fake storefronts, AI-driven scams, agentic
commerce, adaptive evasion."

**Select `APP_SCAM_LLM`.** Read the panel:

- **What GenAI changed:** "Conversational models sustain thousands of individually tailored
  grooming conversations at once."
- **MITRE ATLAS mapping** — "every vector is mapped to a recognised framework."
- **Expected detection signals** — "declared *before* we run it. That's how we measure
  whether we caught it for the right reason, not by luck."

**Say the key line:** "This is the hardest case in payments. The genuine cardholder, on
their own device, with real 3-D Secure authentication, willingly authorises the payment.
Every credential signal is clean. Only the intent is wrong. Most detectors implicitly assume
compromised credentials — this one isn't."

**Set strength to 0.8 → Launch campaign.**

**Show the result card:**
- detection rate
- **signal attribution** — which declared signals actually fired, with the misses shown
- behavioural changes the attack introduced

**Say:** "Signals that don't fire are shown, not hidden. Five of our 47 declared signals
need data outside an authorization message — dispute lifecycle, session telemetry — and
we name them rather than letting a gap look mysterious."

**Optional second launch:** `AGENT_PROMPT_INJECTION` — sets up the security beat later.

---

## 3:45 — Live stream (45s)

**Screen:** Live Stream.

**Say:** "The scored authorization feed. Risk score, band, recommended action — allow, review,
step up, block. Ground truth is shown alongside, because this is a lab, not production."

Tick **Show only high & critical** — "and here's the queue an analyst would actually work."

---

## 4:30 — Explainability (1min 15s)

**Screen:** Investigate. Click the top alert.

**Say:** "Three things a fraud analyst needs: the decision, why, and what would change it."

**Walk the panels:**

1. **Decision** — calibrated risk, recommended action, the payment's actual attributes
   (3-D Secure status, AVS result, SCA exemption claimed).
2. **Exact score decomposition** — "these are additive contributions to the arbiter's
   log-odds. Not an estimate — this is the arithmetic that produced the score. We verify it
   against the model's own decision function in the test suite."
3. **Reason codes** — analyst language, ranked by weight.
4. **Counterfactual** — "what would have to change for this to score benign."

**Then the honesty beat, deliberately:** point at the caveat. "We do *not* claim per-row
attribution inside the gradient-boosted component. SHAP wasn't installable in this
environment, so rather than ship an approximate explainer and call it attribution, we
architected the system so its explanation is exact by construction. The model's importance
is reported globally and labelled as global."

**Why say this out loud:** it signals you know the difference between an explanation and a
plausible story — and the literature shows fluent rationales raise analyst confidence
without raising accuracy.

---

## 5:45 — Fraud network (45s)

**Screen:** Fraud Network.

**Say:** "Rings are invisible per transaction and obvious as structure. This is the subgraph
induced by *shared* infrastructure only — entities touching two or more distinct cards.
Unpruned, it's mostly singleton pairs and the structure disappears."

**Point at the right panel:** "One device linked to 31 distinct cards. No single transaction
looks wrong. The graph does."

**Add:** "This stage runs on the riskiest 20% of traffic — an explicit compute budget, not a
score threshold, which is how production cascades hold p99 inside an authorization window."

---

## 6:30 — Performance & audit (45s)

**Screen:** Performance.

Three things to land:

1. **Temporal split with a delay block** — "we discard 5% of the timeline between train and
   test, because chargeback labels arrive weeks late. Random splits leak the future."
2. **Per-attack recall, worst first** — "the hard cases are meant to be hard. 12 of 25
   vectors are deliberately built to overlap legitimate behaviour."
3. **Zero-day table** — "six vectors removed from training entirely, 0.718 recall at a
   threshold calibrated on seen traffic only."

**If asked about the 1% alert-budget recall (0.334):** "That's bounded by the budget, not
the model — the mathematical ceiling at this prevalence is 0.336. We're at 99.7% of the
maximum any detector could achieve within that review capacity. The prevalence-matched
figure is 0.909."

**Screen:** Audit Trail — "every environment change, campaign and analyst action is recorded
append-only. Model governance expects decisions to be reconstructable."

---

## 7:15 — Close (30s)

**Say:** "Three things I'd want you to take away.

First, this is a **loop**, not a pipeline — the attacks train the defence, and per-signal
recall tells us exactly where the defence is blind, which becomes the next attack.

Second, the attacks are **feasible**. The open problem in adversarial ML on tabular data is
that papers perturb features an attacker can't control. Ours only manipulate what an
attacker really controls — amount, timing, cadence, merchant, device, sequencing.

Third — Mastercard is already ahead of the market here. Threat Scan simulates *known*
attacks against issuers, and AI Garage has published on adversarial fraud generation. This
extends that direction: generated novel attacks instead of replayed known ones, constrained
to be realistic, wired into a continuous loop, and graded per-signal."

---

## Recovery if something fails

| Problem | Fix |
|---|---|
| Boot screen doesn't appear | Backend not running — check `curl localhost:8000/api/health` |
| "Environment not initialised" | Click Start environment; boot takes 5–15s |
| Performance panel is empty | Run `.venv/bin/python -m backend.app.evaluate` to produce `artifacts/metrics.json` |
| Live stream shows nothing | Replay is finite (last 600 transactions). Switch tabs and back to restart it |
| Graph looks sparse | Lower **min risk**, or launch a ring attack (`MULE_FANOUT`, `COORDINATED_RING`) |

**Fallback:** `artifacts/screenshots/` holds eight full-page captures of every panel,
generated by `scripts/ui_smoke.py`. If the live demo fails, present those — they are real
captures of this system, not mockups.

---

## Reproducing the demo from scratch

```bash
git clone <repo> && cd ThreatForge
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m backend.app.evaluate         # generates metrics (~3 min)
cd frontend && npm install && cd ..
./scripts/verify.sh                              # confirm everything is green

.venv/bin/uvicorn backend.app.api:app --port 8000    # terminal 1
cd frontend && npm run dev                            # terminal 2
```
