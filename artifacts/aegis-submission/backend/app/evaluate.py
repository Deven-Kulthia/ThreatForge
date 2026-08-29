"""Evaluation harness — every reported number is produced here.

No metric in this project is hand-written. `python -m backend.app.evaluate` regenerates
`artifacts/metrics.json` and `docs/evaluation.md` from a clean run.

Methodology choices, each deliberate:
  * TEMPORAL split with a DELAY BLOCK. Random splits leak future information. The delay
    block reflects an operational fact: chargeback and investigator labels arrive late, so
    a model deployed today cannot have been trained on last week's still-unlabelled fraud.
  * PR-AUC as the headline, not ROC-AUC. Under heavy imbalance ROC-AUC is optimistic and
    misleading; both are reported so the gap is visible.
  * Recall at a FIXED ALERT RATE. Unconstrained recall is meaningless to an operations
    team with finite review capacity.
  * VALUE detection rate and INSULT rate — fraud is a money problem and false declines
    have a customer cost.
  * Calibration (Brier, ECE) and LATENCY percentiles. A 2026 survey of 49 sources found
    that among 18 fraud sources none reported latency, cost or calibration. We report all.
  * PER-SIGNAL recall: did we catch the attack for the RIGHT REASON, not just catch it.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
)

from .attacks import TAXONOMY, run_all
from .detect import RULE_NAMES, UNIMPLEMENTED_SIGNALS, Detector
from .features import build_features
from .fidelity import assess as assess_fidelity
from .generator import build_population, generate_legit

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
DOCS = ROOT / "docs"

# Operating point: the fraction of traffic an analyst team can review per period.
ALERT_RATE = 0.01
# Label-arrival delay, expressed as a fraction of the timeline held out between
# train and test so no post-decision information can reach the model.
DELAY_FRACTION = 0.05


def build_dataset(
    n_cards: int = 1200,
    n_merchants: int = 200,
    days: int = 45,
    strength: float = 0.6,
    seed: int = 42,
    waves: int = 3,
) -> tuple[pd.DataFrame, list]:
    """Synthetic environment plus `waves` rotated passes of the full attack taxonomy.

    Multiple rotated waves matter: with a single pass, each attack type occupies one point
    in the timeline, so a temporal split holds out whole attack types and the result
    answers "does this generalise to unseen fraud typologies?" rather than "does this
    detect fraud?". Both are worth knowing, so we make the standard evaluation fair here
    and measure the harder question separately in `zero_day_experiment`.
    """
    pop = build_population(n_cardholders=n_cards, n_merchants=n_merchants, seed=seed)
    hist = generate_legit(pop, days=days, seed=seed + 1)
    camps: list = []
    for w in range(max(1, waves)):
        camps += run_all(pop, hist, strength=strength, seed=seed + 2 + w * 100,
                         phase=w / max(waves, 1))
    df = (
        pd.concat([hist] + [c.transactions for c in camps], ignore_index=True)
        .sort_values("timestamp", kind="stable")
        .reset_index(drop=True)
    )
    return df, camps


def temporal_split(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Train / delay-gap / test indices. The gap is discarded, not used by either side."""
    n = len(df)
    tr_end = int(n * 0.65)
    te_start = int(n * (0.65 + DELAY_FRACTION))
    return np.arange(tr_end), np.arange(te_start, n)


def _recall_at_alert_rate(y: np.ndarray, s: np.ndarray, rate: float) -> dict:
    k = max(1, int(round(len(s) * rate)))
    idx = np.argsort(-s)[:k]
    tp = int(y[idx].sum())
    total_pos = int(y.sum())
    return {
        "alert_rate": rate,
        "alerts": k,
        "recall": tp / total_pos if total_pos else 0.0,
        "precision": tp / k,
        "threshold": float(s[idx[-1]]),
    }


def _ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error over equal-width probability bins."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    e = 0.0
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= 1.0)
        if m.sum():
            e += (m.sum() / len(p)) * abs(y[m].mean() - p[m].mean())
    return float(e)


def _reliability(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    out = []
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= 1.0)
        if m.sum():
            out.append({"bin": f"{edges[i]:.1f}-{edges[i+1]:.1f}", "n": int(m.sum()),
                        "predicted": round(float(p[m].mean()), 4),
                        "observed": round(float(y[m].mean()), 4)})
    return out


def _bootstrap_ap(y: np.ndarray, s: np.ndarray, n: int = 200, seed: int = 0) -> list[float]:
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n):
        i = rng.integers(0, len(y), len(y))
        if y[i].sum() > 0:
            vals.append(average_precision_score(y[i], s[i]))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return [round(float(lo), 4), round(float(hi), 4)]


def _latency(det: Detector, df: pd.DataFrame, n: int = 150, ctx_rows: int = 2_000,
             seed: int = 0) -> dict:
    """Latency, split into the two costs that behave completely differently in production.

    `decision_ms` — the inline cost: rules, model inference, graph stage and arbiter for
    ONE transaction whose features are already available. This is the path that sits inside
    an authorization budget.

    `feature_build_ms_per_row` — our batch feature recompute, amortised per row. A real
    deployment does NOT do this per authorization; a streaming feature store maintains
    windowed aggregates incrementally. We report it separately and explicitly rather than
    folding it into a headline number, because folding it in would misrepresent the
    architecture in both directions — it overstates inline cost and hides the real
    engineering dependency (an incremental feature store).
    """
    rng = np.random.default_rng(seed)
    ctx = df.iloc[:ctx_rows]
    pool = np.arange(ctx_rows, min(ctx_rows + 2_000, len(df)))
    if len(pool) == 0:
        pool = np.arange(max(len(df) - 1, 1))
    idx = rng.choice(pool, size=min(n, len(pool)), replace=False)

    # Amortised batch feature-build cost.
    batch = df.iloc[: min(ctx_rows + 500, len(df))]
    t = time.perf_counter()
    build_features(batch)
    feat_ms_per_row = (time.perf_counter() - t) * 1000.0 / max(len(batch), 1)

    # Inline decision cost, features supplied.
    times = []
    for i in idx:
        one = pd.concat([ctx, df.iloc[[i]]], ignore_index=True)
        Xr = build_features(one).iloc[-1:]          # outside the timed region
        row = one.iloc[-1:]
        t = time.perf_counter()
        det.score(row, X=Xr)
        times.append((time.perf_counter() - t) * 1000.0)

    a = np.array(times)
    return {
        "decision_p50_ms": round(float(np.percentile(a, 50)), 2),
        "decision_p95_ms": round(float(np.percentile(a, 95)), 2),
        "decision_p99_ms": round(float(np.percentile(a, 99)), 2),
        "decision_mean_ms": round(float(a.mean()), 2),
        "feature_build_ms_per_row_batch": round(feat_ms_per_row, 4),
        "samples": len(a),
        "context_rows": int(ctx_rows),
        "note": "decision_* is the inline path with features supplied; the batch feature "
                "recompute is reported separately and would be incremental in production",
    }


def zero_day_experiment(df: pd.DataFrame, holdout: int = 6, seed: int = 3) -> dict:
    """Can the defence catch attack types it has NEVER seen?

    Entire attack vectors are removed from training, then scored at test time. This is the
    question that matters for a closed-loop system: novel fraud is by definition absent
    from the training label set, and a detector that only recognises memorised typologies
    is useless against it.
    """
    rng = np.random.default_rng(seed)
    vectors = sorted(TAXONOMY)
    unseen = set(rng.choice(vectors, size=min(holdout, len(vectors)), replace=False))

    at = df["attack_type"].to_numpy()
    is_unseen = np.isin(at, list(unseen))
    train_df = df[~is_unseen].reset_index(drop=True)

    det = Detector().fit(train_df, train_df["is_fraud"].to_numpy())
    scored = det.score(df)
    s = scored["risk_score"].to_numpy()
    y = df["is_fraud"].to_numpy()

    # Operating point set on traffic the model did see, then applied to unseen vectors.
    seen_mask = ~is_unseen
    op = _recall_at_alert_rate(y[seen_mask], s[seen_mask], ALERT_RATE)
    thr = op["threshold"]

    per_vec = {}
    for v in sorted(unseen):
        m = at == v
        if m.sum():
            per_vec[v] = {"n": int(m.sum()),
                          "recall_at_seen_threshold": round(float((s[m] >= thr).mean()), 4),
                          "mean_risk": round(float(s[m].mean()), 4),
                          "hard_to_detect": TAXONOMY[v].hard_to_detect}

    unseen_fraud = is_unseen & (y == 1)
    return {
        "held_out_vectors": sorted(unseen),
        "threshold_from_seen_traffic": round(float(thr), 4),
        "unseen_transactions": int(unseen_fraud.sum()),
        "unseen_recall": round(float((s[unseen_fraud] >= thr).mean()), 4)
        if unseen_fraud.sum() else 0.0,
        "per_vector": per_vec,
        "interpretation": "recall on fraud typologies entirely absent from training, "
                          "measured at an operating point calibrated on seen traffic only",
    }


def evaluate(verbose: bool = True) -> dict:
    df, camps = build_dataset()
    y_all = df["is_fraud"].to_numpy()
    tr, te = temporal_split(df)

    det = Detector().fit(df.iloc[tr], y_all[tr])

    X_te = build_features(df.iloc[te])
    scored = det.score(df.iloc[te], X=X_te)
    y = y_all[te]
    s = scored["risk_score"].to_numpy()
    amt = df.iloc[te]["amount"].to_numpy()

    ap = float(average_precision_score(y, s))
    roc = float(roc_auc_score(y, s))

    # Best-F1 operating point, reported alongside the capacity-constrained one.
    prec, rec, thr = precision_recall_curve(y, s)
    f1 = np.divide(2 * prec * rec, prec + rec, out=np.zeros_like(prec), where=(prec + rec) > 0)
    bi = int(np.argmax(f1))
    best_thr = float(thr[min(bi, len(thr) - 1)])
    pred = s >= best_thr

    tp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    tn = int(((pred == 0) & (y == 0)).sum())

    # Money view: what share of attempted fraud value would have been stopped.
    vdr = float(amt[(y == 1) & pred].sum() / max(amt[y == 1].sum(), 1e-9))
    insult = float(fp / max(int((y == 0).sum()), 1))

    # Per-attack recall at the capacity-constrained operating point.
    op = _recall_at_alert_rate(y, s, ALERT_RATE)
    flagged = s >= op["threshold"]
    at = df.iloc[te]["attack_type"].to_numpy()
    per_attack = {}
    for aid, spec in TAXONOMY.items():
        m = at == aid
        if m.sum():
            per_attack[aid] = {
                "n": int(m.sum()),
                "recall_at_alert_rate": round(float(flagged[m].mean()), 4),
                "mean_risk": round(float(s[m].mean()), 4),
                "hard_to_detect": spec.hard_to_detect,
                "severity": spec.severity,
                "category": spec.category,
            }

    # PER-SIGNAL recall — was the attack caught for the right reason?
    sig_lists = scored["detected_signals"].tolist()
    per_signal = {}
    for aid, spec in TAXONOMY.items():
        m = np.flatnonzero(at == aid)
        if not len(m):
            continue
        hits = {}
        for want in spec.expected_signals:
            if want in UNIMPLEMENTED_SIGNALS:
                hits[want] = {"status": "not_implemented",
                              "reason": UNIMPLEMENTED_SIGNALS[want]}
            else:
                fired = sum(1 for i in m if want in sig_lists[i]) / len(m)
                hits[want] = {"status": "implemented", "fire_rate": round(float(fired), 4)}
        per_signal[aid] = hits

    impl = [s_ for spec in TAXONOMY.values() for s_ in spec.expected_signals
            if s_ not in UNIMPLEMENTED_SIGNALS]
    covered = sum(1 for s_ in set(impl) if s_ in RULE_NAMES or s_ in
                  {"ring_component", "graph_fanin", "injection_pattern_in_text"})

    metrics = {
        "generated_at_utc": pd.Timestamp.now("UTC").isoformat(),
        "dataset": {
            "transactions": int(len(df)),
            "fraud": int(y_all.sum()),
            "fraud_rate": round(float(y_all.mean()), 5),
            "cards": int(df["card_token"].nunique()),
            "merchants": int(df["merchant_id"].nunique()),
            "days": int((df["timestamp"].max() - df["timestamp"].min()).days),
            "attack_vectors": len(TAXONOMY),
            "campaigns": len(camps),
            "synthetic": True,
        },
        "split": {"method": "temporal with delay block", "train": int(len(tr)),
                  "test": int(len(te)), "delay_fraction": DELAY_FRACTION,
                  "test_fraud_rate": round(float(y.mean()), 5)},
        "discrimination": {
            "pr_auc": round(ap, 4),
            "pr_auc_95ci": _bootstrap_ap(y, s),
            "roc_auc": round(roc, 4),
            "note": "PR-AUC is the headline; ROC-AUC is reported for comparability and "
                    "is optimistic under imbalance",
        },
        "operating_point_best_f1": {
            "threshold": round(best_thr, 4),
            "precision": round(tp / max(tp + fp, 1), 4),
            "recall": round(tp / max(tp + fn, 1), 4),
            "f1": round(float(f1[bi]), 4),
            "false_positive_rate": round(fp / max(fp + tn, 1), 5),
            "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        },
        "operating_point_capacity_constrained": {
            **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in op.items()},
            "rationale": "recall achievable within a 1% daily review budget",
            "recall_ceiling": round(float(min(1.0, ALERT_RATE / max(y.mean(), 1e-9))), 4),
            "ceiling_note":
                "Recall here is BOUNDED BY THE BUDGET, not by the model: with a "
                f"{ALERT_RATE:.0%} alert budget and {y.mean():.2%} test prevalence, no "
                "detector could exceed the ceiling shown. Read this number as "
                "'value captured per unit of analyst effort', not as model recall.",
        },
        "operating_point_prevalence_matched": {
            **{k: (round(v, 4) if isinstance(v, float) else v)
               for k, v in _recall_at_alert_rate(y, s, float(y.mean())).items()},
            "rationale": "alert budget sized to actual prevalence, so recall is not "
                         "budget-capped and reflects the detector rather than the queue",
        },
        "prevalence_note":
            f"Synthetic fraud prevalence here is {float(y_all.mean()):.2%}, deliberately "
            "higher than the ~0.1-1% seen in live card portfolios (PSD2 RTS Annex reference "
            "bands are 1-13 bps; Stripe reports ~1 in 1,000). A higher rate is required to "
            "train and evaluate 25 distinct attack vectors on a synthetic corpus. "
            "Threshold-dependent metrics (precision, alert-rate recall, insult rate) are "
            "prevalence-sensitive and would shift in a live portfolio; PR-AUC, calibration "
            "and latency are the more transferable figures.",
        "money_and_customer_impact": {
            "value_detection_rate": round(vdr, 4),
            "fraud_value_attempted": round(float(amt[y == 1].sum()), 2),
            "fraud_value_stopped": round(float(amt[(y == 1) & pred].sum()), 2),
            "insult_rate": round(insult, 5),
            "insult_rate_note": "share of legitimate payments declined at the best-F1 point",
        },
        "calibration": {
            "brier": round(float(brier_score_loss(y, s)), 5),
            "ece_10bin": round(_ece(y, s), 5),
            "reliability": _reliability(y, s),
            "method": "isotonic regression on a held-out temporal slice",
        },
        "latency": _latency(det, df),
        "cascade": {
            "graph_stage_share": round(float(scored["graph_evaluated"].mean()), 4),
            "rationale": "expensive graph stage runs only on the riskiest slice",
        },
        "coverage": {
            "attack_vectors_simulated": len(TAXONOMY),
            "categories": len({s_.category for s_ in TAXONOMY.values()}),
            "rule_signals_implemented": len(RULE_NAMES),
            "expected_signals_distinct": len(set(impl)),
            "expected_signals_covered": covered,
            "signals_not_implemented": UNIMPLEMENTED_SIGNALS,
        },
        "per_attack": per_attack,
        "per_signal_recall": per_signal,
        "zero_day": zero_day_experiment(df),
        "fidelity": assess_fidelity(df),
    }

    ARTIFACTS.mkdir(exist_ok=True)
    (ARTIFACTS / "metrics.json").write_text(json.dumps(metrics, indent=2))
    _write_report(metrics)

    if verbose:
        d, disc = metrics["dataset"], metrics["discrimination"]
        print(f"dataset      {d['transactions']:,} txns · {d['fraud']:,} fraud "
              f"({d['fraud_rate']:.2%}) · {d['attack_vectors']} vectors")
        print(f"PR-AUC       {disc['pr_auc']:.4f}  95% CI {disc['pr_auc_95ci']}")
        print(f"ROC-AUC      {disc['roc_auc']:.4f}")
        f1b = metrics["operating_point_best_f1"]
        print(f"best-F1      P {f1b['precision']:.3f} · R {f1b['recall']:.3f} · "
              f"F1 {f1b['f1']:.3f} · FPR {f1b['false_positive_rate']:.4f}")
        print(f"@1% alerts   recall {op['recall']:.3f} · precision {op['precision']:.3f} "
              f"(budget ceiling {metrics['operating_point_capacity_constrained']['recall_ceiling']:.3f})")
        pm = metrics["operating_point_prevalence_matched"]
        print(f"@prevalence  recall {pm['recall']:.3f} · precision {pm['precision']:.3f}")
        m = metrics["money_and_customer_impact"]
        print(f"value        VDR {m['value_detection_rate']:.3f} · "
              f"insult {m['insult_rate']:.4f}")
        c = metrics["calibration"]
        print(f"calibration  Brier {c['brier']:.4f} · ECE {c['ece_10bin']:.4f}")
        lat = metrics["latency"]
        print(f"latency      decision p50 {lat['decision_p50_ms']}ms · "
              f"p95 {lat['decision_p95_ms']}ms · p99 {lat['decision_p99_ms']}ms")
        print(f"             feature build {lat['feature_build_ms_per_row_batch']}ms/row (batch)")
        zd = metrics["zero_day"]
        print(f"zero-day     recall {zd['unseen_recall']:.3f} on "
              f"{len(zd['held_out_vectors'])} held-out vectors "
              f"({zd['unseen_transactions']} txns)")
        print(f"cascade      graph on {metrics['cascade']['graph_stage_share']:.1%}")
        print(f"artifacts    {ARTIFACTS/'metrics.json'}")
    return metrics


def _write_report(m: dict) -> None:
    d, sp, disc = m["dataset"], m["split"], m["discrimination"]
    f1b, op = m["operating_point_best_f1"], m["operating_point_capacity_constrained"]
    pm = m["operating_point_prevalence_matched"]
    mo, cal, lat = m["money_and_customer_impact"], m["calibration"], m["latency"]

    rows = sorted(m["per_attack"].items(),
                  key=lambda kv: kv[1]["recall_at_alert_rate"])
    tbl = "\n".join(
        f"| {k} | {v['category']} | {v['n']} | {v['recall_at_alert_rate']:.3f} | "
        f"{v['mean_risk']:.3f} | {'yes' if v['hard_to_detect'] else 'no'} | {v['severity']} |"
        for k, v in rows
    )
    rel = "\n".join(
        f"| {r['bin']} | {r['n']} | {r['predicted']:.3f} | {r['observed']:.3f} |"
        for r in cal["reliability"]
    )
    zd = m["zero_day"]
    zdt = "\n".join(
        f"| {k} | {v['n']} | {v['recall_at_seen_threshold']:.3f} | {v['mean_risk']:.3f} | "
        f"{'yes' if v['hard_to_detect'] else 'no'} |"
        for k, v in sorted(zd["per_vector"].items(),
                           key=lambda kv: kv[1]["recall_at_seen_threshold"])
    )

    fid = m["fidelity"]
    fid_rows = "\n".join(
        f"| {k.replace('_', ' ')} | {v['value']} | {v['reference_band'][0]}–"
        f"{v['reference_band'][1]} | {'yes' if v['within_band'] else 'NO'} |"
        for k, v in fid["realism"].items() if isinstance(v, dict)
    )
    fid_fields = "\n".join(
        f"| {k} | {v['univariate_auc']:.3f} | {v['overlap']:.3f} |"
        for k, v in sorted(fid["separability"]["per_field"].items(),
                           key=lambda kv: -kv[1]["univariate_auc"])
    )
    fid_camo = "\n".join(
        f"- `{k}` — mean overlap {v:.3f}"
        for k, v in fid["separability"]["most_camouflaged_vectors"].items()
    )

    DOCS.mkdir(exist_ok=True)
    (DOCS / "evaluation.md").write_text(f"""# Evaluation Results

**Generated:** {m['generated_at_utc']} · **Reproduce:** `python -m backend.app.evaluate`

Every number on this page is computed by `backend/app/evaluate.py`. None is hand-written.
All data is synthetic.

## Dataset

| | |
|---|---|
| Transactions | {d['transactions']:,} |
| Fraud | {d['fraud']:,} ({d['fraud_rate']:.2%}) |
| Cards / merchants | {d['cards']:,} / {d['merchants']:,} |
| Window | {d['days']} days |
| Attack vectors | {d['attack_vectors']} across {m['coverage']['categories']} categories |

## Split

**{sp['method']}.** Train {sp['train']:,} · Test {sp['test']:,} · delay gap
{sp['delay_fraction']:.0%} of the timeline discarded between them, reflecting late label
arrival. Test-set fraud rate {sp['test_fraud_rate']:.2%}.

## Discrimination

| Metric | Value |
|---|---|
| **PR-AUC** (headline) | **{disc['pr_auc']:.4f}** (95% CI {disc['pr_auc_95ci'][0]:.4f}–{disc['pr_auc_95ci'][1]:.4f}) |
| ROC-AUC | {disc['roc_auc']:.4f} |

{disc['note']}.

## Operating points

**Best F1** (threshold {f1b['threshold']:.3f}): precision {f1b['precision']:.3f},
recall {f1b['recall']:.3f}, F1 {f1b['f1']:.3f}, FPR {f1b['false_positive_rate']:.4f}.
Confusion — TP {f1b['confusion']['tp']}, FP {f1b['confusion']['fp']},
FN {f1b['confusion']['fn']}, TN {f1b['confusion']['tn']}.

**Capacity-constrained** ({op['alert_rate']:.0%} review budget, {op['alerts']} alerts):
recall {op['recall']:.3f}, precision {op['precision']:.3f}. {op['rationale']}.

> ⚠️ {op['ceiling_note']} Ceiling for this split: **{op['recall_ceiling']:.3f}**.

**Prevalence-matched** ({pm['alert_rate']:.2%} budget, {pm['alerts']} alerts):
recall {pm['recall']:.3f}, precision {pm['precision']:.3f}. {pm['rationale']}.

### Prevalence caveat

{m['prevalence_note']}

## Money and customer impact

| Metric | Value |
|---|---|
| Value detection rate | {mo['value_detection_rate']:.3f} |
| Fraud value attempted | {mo['fraud_value_attempted']:,.2f} |
| Fraud value stopped | {mo['fraud_value_stopped']:,.2f} |
| Insult rate | {mo['insult_rate']:.4f} |

> Absolute values are summed over `amount` across a multi-currency synthetic population,
> so they carry no single currency unit. Read the **ratio** (value detection rate), not the
> absolute totals.

## Fidelity evidence (criterion 2)

Fidelity is judged instrumentally, so it is measured rather than asserted.
{fid['summary']}.

### Generated marginals vs published reference bands

| Measure | Value | Reference band | In band |
|---|---|---|---|
{fid_rows}

Bands are sourced from public references (PSD2 RTS Annex fraud-rate bands, Nigrini's MAD
thresholds for Benford conformity) and are deliberately wide — they are sanity bands for a
synthetic corpus, not targets to overfit.

### Non-separability of attack traffic

If attacks came from an obviously different process, any classifier would score ~1.0 and the
whole evaluation would be meaningless. Measured on **raw** authorization fields, not
engineered features:

| Raw field | Univariate AUC | Attack/legit overlap |
|---|---|---|
{fid_fields}

Max univariate AUC **{fid['separability']['max_univariate_auc']}**, mean attack/legit overlap
**{fid['separability']['mean_overlap']}**. {fid['separability']['interpretation']}

Most camouflaged vectors (highest overlap with legitimate traffic):
{fid_camo}

## Calibration

Brier {cal['brier']:.5f} · ECE (10-bin) {cal['ece_10bin']:.5f} · method: {cal['method']}.

| Bin | n | Predicted | Observed |
|---|---|---|---|
{rel}

## Latency

Two costs, reported separately because they behave differently in production.

| | |
|---|---|
| **Inline decision** (rules + model + graph + arbiter, features supplied) | **p50 {lat['decision_p50_ms']} ms · p95 {lat['decision_p95_ms']} ms · p99 {lat['decision_p99_ms']} ms** |
| Batch feature recompute, amortised | {lat['feature_build_ms_per_row_batch']} ms/row |

n={lat['samples']}, context {lat['context_rows']:,} rows. {lat['note']}.

Cascade: the graph stage evaluates {m['cascade']['graph_stage_share']:.1%} of traffic.

## Zero-day generalisation

The hardest question for a closed-loop system: **can the defence catch fraud typologies it
has never seen?** {len(zd['held_out_vectors'])} attack vectors were removed from training
entirely, then scored at an operating point calibrated on seen traffic only
(threshold {zd['threshold_from_seen_traffic']:.3f}).

**Recall on unseen vectors: {zd['unseen_recall']:.3f}** across {zd['unseen_transactions']:,}
transactions.

| Held-out vector | n | Recall | Mean risk | Hard by design |
|---|---|---|---|---|
{zdt}

{zd['interpretation']}.

## Per-attack recall at the capacity-constrained operating point

Sorted worst-first — the hard cases are meant to be hard.

| Attack | Category | n | Recall | Mean risk | Hard by design | Severity |
|---|---|---|---|---|---|---|
{tbl}

## Signal coverage

{m['coverage']['rule_signals_implemented']} rule signals implemented, covering
{m['coverage']['expected_signals_covered']} of {m['coverage']['expected_signals_distinct']}
distinct signals the taxonomy expects. Signals we deliberately do **not** implement, and why:

{chr(10).join(f'- `{k}` — {v}' for k, v in m['coverage']['signals_not_implemented'].items())}

Per-signal fire rates per attack are in `artifacts/metrics.json` under `per_signal_recall`.
This is how we verify an attack was caught *for the right reason* rather than by accident.
""")


if __name__ == "__main__":
    evaluate()
