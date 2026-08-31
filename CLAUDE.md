# CLAUDE.md — Aegis (Mastercard Innovation Challenge 2026)

## Objective
Closed-loop adversarial AI system for payment fraud: **Identify → Generate → Defend**.
Attacks we generate train and stress-test the defense; defensive gaps generate new attacks.
Submission: code repo + walkthrough deck + web prototype. Deadline **31 Aug 2026 23:59 IST**.

## Judged on (official)
Primary 5: attack **diversity** · simulation **fidelity** · detection **efficacy** · **novelty** ·
**real-world feasibility in live payments**.
Secondary 9 (Rules §8): innovation, originality, technical quality, relevance to challenge
statement, effectiveness, feasibility, scalability, commercial viability, presentation quality.

## Hard constraints (competition rules — non-negotiable)
- Synthetic data ONLY. No real cardholder data, PII, or production payment data.
- Attack simulator must be **network-isolated by construction**. Never target live systems.
- Dependencies must be OSI-approved permissive (MIT/BSD/Apache-2.0). No AGPL.
- Repo is **public** and named after the team (`ThreatForge`) — host submission guide Step 4
  supersedes the earlier private-repo reading of Foundational §6a.
- Submit the writeup EARLY — draft ≠ submitted = disqualified.

## Directory map
```
research/      Phase-1 research (competition.md is authoritative on rules)
docs/          current-state.md, architecture.md, decisions.md, demo-flow.md
backend/app/   schema, generator, attacks, features, detect, explain, evaluate, api
backend/tests/ pytest
frontend/      Vite+React+TS+Tailwind dashboard
.venv/         Python 3.14 venv
```

## Commands
```bash
.venv/bin/python -m pytest backend/tests -q        # tests
.venv/bin/python -m backend.app.evaluate           # reproduce metrics
.venv/bin/uvicorn backend.app.api:app --reload     # API :8000
cd frontend && npm run dev                         # UI :5173
```

## Stack + why
Python 3.14 · FastAPI · scikit-learn · pandas · networkx · SQLite (stdlib) · React/Vite/Tailwind.
**No lightgbm/shap** — libomp unavailable (no Homebrew) and numba fails to build on 3.14.
Use `HistGradientBoostingClassifier` + intrinsically-additive explainer instead. See docs/decisions.md.

## Conventions
- Every synthetic record carries `synthetic: true`. UI labels all data as synthetic.
- Attacks emit ground-truth metadata (attack_type, scenario_id, strength, expected_signals).
- No fabricated metrics. All numbers come from `evaluate.py` runs.
- Small patches over rewrites. Don't reread unchanged files.

## Current milestone
See `docs/current-state.md`.
