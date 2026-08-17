# Current State

**Updated:** 2026-08-17 · **Phase:** vertical slice build

## Architecture (current)
```
generator.py  synthetic population + legit auth traffic (ISO-8583-inspired schema)
attacks.py    attack taxonomy → campaigns emitting ground-truth metadata
features.py   velocity / behavioral-drift / graph features
detect.py     cascade: rules → HistGradientBoosting → graph signals → ensemble
explain.py    additive reason codes (exact, no SHAP dep)
evaluate.py   PR-AUC, recall@1% alert rate, latency p50/p99, calibration
api.py        FastAPI + WebSocket stream
frontend/     React dashboard
```

## Completed
- Phase 1 research: `research/competition.md` (rules verified), `research/existing-solutions.md` Part A
- Registration confirmed (Kaggle rules accepted)
- venv + dependency stack verified

## In progress
- Vertical slice: schema → generator → attack → detect → score → explain

## Next
1. schema.py + generator.py + test
2. attacks.py (first 3 vectors) + test
3. features.py + detect.py + evaluate.py
4. api.py + frontend slice
5. Expand attack taxonomy to 20+

## Key decisions
- No lightgbm/shap (libomp + numba unavailable on py3.14) → sklearn HistGB + additive explainer
- No GNN — GADBench: trees + neighbor-aggregated features outperform tailored GNNs
- Reject SMOTE (leakage + multimodal minority); use `class_weight`/`scale_pos_weight`
- LLM off the critical path (explanation only, never the block decision)

## Known bugs
None yet.

## Test status
Not yet run.
