# Current State

**Updated:** 2026-08-17 · **Phase:** documentation complete; deck + judge simulation next

## Architecture
```
generator.py  synthetic population + legitimate traffic (ISO-8583-inspired schema)
attacks.py    25-vector taxonomy → campaigns with full ground-truth metadata
features.py   57 strictly causal features (velocity / own-baseline / graph / verification)
detect.py     cascade: 39 rules → HistGradientBoosting → graph (top 20%) → arbiter → isotonic
explain.py    exact additive reason codes (no SHAP dependency)
evaluate.py   PR-AUC, operating points, calibration, latency, per-signal, zero-day
api.py        FastAPI + WebSocket + SQLite audit trail
frontend/     7-panel React command centre
```

## Completed
- **Research:** competition rules verified, threat landscape, existing solutions, sources (4 docs)
- **Backend:** all 8 modules, each with a passing self-check
- **Frontend:** 7 panels, typechecks clean, builds, verified in a real browser
- **Tests:** 113 passing across 4 suites (data pipeline, detection, security, API)
- **Verification gate:** `scripts/verify.sh --full` — self-checks, tests, compliance scan, typecheck, build, browser smoke
- **Docs:** architecture, decisions, threat-model, fraud-taxonomy (generated), detection-methodology, evaluation (generated), security, demo-flow, deployment, README
- **Pushed:** 5 commits to private repo `Deven-Kulthia/aegis-ai-defence-lab`

## Verified metrics (`artifacts/metrics.json`)
PR-AUC **0.957** (CI 0.946–0.969) · ROC-AUC 0.996 · best-F1 **0.934** (P 0.989 / R 0.885) ·
FPR 0.0003 · decision **p50 16.6ms / p99 31.4ms** · zero-day recall **0.781** ·
ECE 0.0019 · VDR 0.913 · 90,256 txns at 3.83% fraud

## Next
1. Walkthrough deck (.pptx) — required submission artifact
2. Judge simulation against all 14 official criteria, then fix what it surfaces
3. Kaggle writeup + final submission audit
4. Presenter's walkthrough for the user

## Key decisions
- No lightgbm/shap (libomp + numba unavailable on py3.14) → sklearn HistGB + exact additive explainer
- No GNN — GADBench: trees + neighbour aggregation outperform tailored GNNs
- No SMOTE — leakage + multimodal minority; use `class_weight="balanced"`
- LLM off the critical path (narration only, never the block decision)
- Cascade gated by compute budget (top 20%), not an absolute score threshold
- Positioning: extends Mastercard's own published direction (Threat Scan, AI Garage ICAIF papers) — not a new category

## Competition constraints
- Deadline **31 Aug 2026 23:59 IST**; draft ≠ submitted = not considered
- Three artifacts required: code repo · walkthrough deck/doc · working web prototype
- Synthetic data only; simulator network-isolated (enforced by AST test)
- Dependencies OSI-permissive only (Kaggle §6c)
- Repo stays private until judging concludes (Kaggle §6a)

## Known bugs
None open. Fixed this session: duplicate transaction_ids across same-type campaigns;
WebSocket false-failure under StrictMode double-mount; unreadable alert-band chart;
graph rendering as noise before shared-infrastructure pruning.

## Test status
113 passed · 5 module self-checks green · tsc clean · vite build clean · browser demo path verified
