# Deployment

Two parts: **§1** reproducing the prototype (what a judge or reviewer needs), and **§2** what
a real deployment would require — stated honestly rather than implied.

---

# §1 — Running the prototype

## Prerequisites

| Requirement | Version used | Notes |
|---|---|---|
| Python | 3.14 | 3.11+ should work; 3.14 is what this was built and tested on |
| Node.js | 24 | 20+ should work |
| Disk | ~400 MB | Mostly `node_modules` |
| Network | Install only | The system runs fully offline once installed |

No database server, no Docker, no Redis, no API key. That is deliberate — see
[`decisions.md`](decisions.md) D12.

## Install

```bash
git clone <repository-url>
cd aegis-ai-defence-lab

# backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# frontend
cd frontend && npm install && cd ..
```

### If `npm install` fails with a cache permission error

A pre-existing corrupted npm cache is a common local condition. Use a scratch cache rather
than modifying the global one:

```bash
cd frontend && npm install --cache /tmp/npm-cache-aegis
```

## Generate metrics

```bash
.venv/bin/python -m backend.app.evaluate
```

Takes roughly 3–5 minutes. Writes `artifacts/metrics.json` and regenerates
[`evaluation.md`](evaluation.md). The Performance panel reads this artifact, so run it before
demoing.

## Verify everything

```bash
./scripts/verify.sh            # backend: self-checks, 113 tests, compliance scan
./scripts/verify.sh --full     # also frontend typecheck, build, and browser smoke test
```

The gate must exit 0 before any push. It fails on staged secrets, tracked build artifacts,
tracked competition page captures, and credential patterns in source.

## Run

```bash
# terminal 1 — API on :8000
.venv/bin/uvicorn backend.app.api:app --port 8000

# terminal 2 — dashboard on :5173
cd frontend && npm run dev
```

Open **http://localhost:5173** and click **Start environment** (5–15 seconds).

Vite proxies `/api` and `/ws` to port 8000, so the browser stays same-origin and no CORS
relaxation is needed in the demo path.

## Production-style frontend build

```bash
cd frontend && npm run build && npm run preview     # serves the built bundle on :4173
```

Bundle: ~672 kB raw, ~192 kB gzipped.

## Useful commands

```bash
.venv/bin/python -m backend.app.generator    # synthetic traffic self-check
.venv/bin/python -m backend.app.attacks      # simulate all 25 vectors
.venv/bin/python -m backend.app.features     # feature causality check
.venv/bin/python -m backend.app.detect       # train and score
.venv/bin/python -m backend.app.explain      # explanation exactness check
.venv/bin/python -m backend.app.api          # in-process API self-check

.venv/bin/python -m pytest backend/tests -q  # 113 tests
.venv/bin/python scripts/gen_docs.py         # regenerate fraud-taxonomy.md from code
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/ui_smoke.py
```

The UI smoke test needs both servers running and uses the system Python where Playwright is
installed. It writes eight full-page screenshots to `artifacts/screenshots/`.

## Environment variables

None are required to run the system. `.env` is used only for GitHub operations:

```bash
cp .env.example .env      # then fill in
```

`.env` is git-ignored and must never be committed.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `503 environment not initialised` | Environment not booted | Click **Start environment**, or `POST /api/environment/boot` |
| Performance panel empty | No metrics artifact | `.venv/bin/python -m backend.app.evaluate` |
| `ModuleNotFoundError: lightgbm` | Not used — removed deliberately | Ignore; the stack is sklearn-only |
| `OSError: libomp.dylib` | Stale lightgbm install | `.venv/bin/pip uninstall lightgbm` |
| `shap` fails to build | `numba` has no Python 3.14 wheel | Not a dependency; explainability is native (`decisions.md` D8) |
| Live stream stops | Replay is finite (last 600 transactions) | Switch tabs and back |
| Graph looks sparse | Pruned to shared infrastructure only | Lower **min risk**, or launch `MULE_FANOUT` / `COORDINATED_RING` |
| Port already in use | Previous run still alive | `pkill -f "uvicorn backend.app.api"` |

---

# §2 — What production would actually require

The prototype is honest about being a prototype. This is the gap.

## 2.1 Architecture shape that transfers

The cascade is the durable part:

```
authorization request
    │
    ├─ deterministic rules        all traffic, sub-millisecond
    ├─ gradient-boosted model     all traffic, single-digit ms
    ├─ graph/relational signals   budgeted slice only
    └─ arbiter + calibration      microseconds
```

Cheap checks on everything, expensive relational analysis on a budgeted slice. That maps
directly onto how production fraud systems are built.

## 2.2 What must change

| Concern | Prototype | Production requirement |
|---|---|---|
| **Feature computation** | Batch recompute (0.10 ms/row amortised) | Streaming feature store with incrementally maintained windowed aggregates. This is the single largest engineering item |
| **Model serving** | In-process sklearn | Versioned model registry, champion/challenger, shadow deployment |
| **Graph state** | Recomputed per batch | Incrementally maintained entity graph. Grab documents real-time graph updating as the genuinely hard part |
| **Storage** | In-process DataFrames + SQLite | Event log (Kafka or equivalent) + feature store + warehouse |
| **Labels** | Known by construction | Chargeback and investigator feedback with weeks of delay; the evaluation delay block models this, the feedback-poisoning problem remains open |
| **Auth** | None | SSO + RBAC (analyst / reviewer / admin), per-action authorization on block/allow |
| **Transport** | HTTP localhost | TLS everywhere |
| **Audit** | Append-only by convention | Tamper-evident (hash-chained or write-once) for model governance |
| **Rate limiting** | None | Required — `/api/environment/boot` is expensive |
| **Monitoring** | Metrics artifact | Live drift monitoring, score-distribution alerting, per-segment performance. Noting that pure concept drift is provably invisible to label-free monitoring — hence the generator |

## 2.3 Scaling estimates

Grounded in measured numbers rather than guesses.

- **Decision path:** p99 31 ms measured in-process with features supplied. Stripe reports
  Radar deciding in **<100 ms** while assessing >1,000 characteristics, so the shape of our
  budget is plausible.
- **Throughput:** the model is stateless, so it scales horizontally. The binding constraint
  is feature-store read latency, not inference.
- **Graph stage:** gated to 20% of traffic by design. Feedzai's work on low-latency feature
  engines excludes up to 90% of events from the durable-write path via probabilistic
  thinning — the same pattern would apply here.
- **Cost control:** the compute-budget gate is a tunable dial, not a fixed constant.

## 2.4 Integration surface

Aegis consumes an authorization message and returns a scored decision, so it slots in as a
risk service rather than as infrastructure:

```
POST /score  →  { risk_score, risk_level, recommended_action,
                  detected_signals[], explanation }
```

The schema is modelled on ISO 8583 / EMV / 3-D Secure 2 / PSD2 fields, so mapping from a
real authorization stream is a field-mapping exercise rather than a redesign.

## 2.5 Deployment options, if it were productionised

| Option | Fit |
|---|---|
| Sidecar risk service next to the auth switch | Lowest latency; matches the inline budget |
| Managed container (Cloud Run / ECS Fargate) | Simplest operationally; adds a network hop |
| Issuer-side batch scoring | Loses inline blocking; still useful for mule and ring discovery |

No orchestration is included in this repository because none is needed to evaluate the
submission, and every added service is another way for a live demo to fail.
