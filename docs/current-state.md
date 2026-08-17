# Current State

**Updated:** 2026-08-17 · **Phase:** all three artifacts exist; judge simulation + submit next

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
- **Deck:** `artifacts/aegis-walkthrough.pptx` — 15 slides + speaker notes, generated from
  metrics.json by `scripts/make_deck.py` (so it cannot drift from the code)
- **Writeup:** `docs/submission-writeup.md` — Kaggle Writeups paste target, covers all 14 criteria
- **Presenter guide:** `docs/presenter-guide.md` — run/test commands, 3-length pitch, ~30-question
  judge Q&A bank, memorised-numbers sheet, pre-demo checklist, failure recovery
- **Compliance audit (2026-08-18):** repo confirmed private (unauth API → 404); 41 Python + 121 npm
  packages audited, zero AGPL/GPL/SSPL; 21 security tests enforce synthetic-only, no-PAN,
  Luhn-invalid tokens, truncated IPs, AST-level network isolation, responsible-AI taxonomy check
- **Pushed:** 7 commits to private repo `Deven-Kulthia/aegis-ai-defence-lab`

## Next
1. Judge simulation against all 14 official criteria, then fix what it surfaces
2. **Submit a minimum writeup to Kaggle Writeups EARLY** (draft ≠ submitted = not considered)
3. Presenter's walkthrough for the user

## Submission checklist (P0 — all three or the entry is invalid)
- [x] Artifact 1: code repo, runnable, covers identify/generate/defend
- [x] Artifact 2: walkthrough .pptx with efficacy results
- [x] Artifact 3: working web prototype, presentable UI, shows the closed loop
- [ ] **Writeup actually SUBMITTED on Kaggle** (not left in draft) ← the disqualification risk
- [ ] Re-check the competition page before submitting (Mastercard may amend terms)
- [x] Registration: Kaggle rules accepted (= entry). Registration closes **20 Aug** — confirm any
      separate Luma/Mastercard form is done before then
- [x] Synthetic-only, network-isolated simulator, permissive licences, repo private

## Verified metrics (`artifacts/metrics.json`)
PR-AUC **0.944** (CI 0.931–0.957) · ROC-AUC 0.989 · best-F1 **0.929** (P 0.972 / R 0.891) ·
FPR 0.0008 · decision **p50 13.7ms / p99 18.8ms** · zero-day recall **0.718** ·
ECE 0.0038 · VDR 0.941 · 90,258 txns at 3.83% fraud

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
113 passed · 6 module self-checks green · tsc clean · vite build clean · browser demo path verified
