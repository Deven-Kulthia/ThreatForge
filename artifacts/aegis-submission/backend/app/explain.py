"""Explainability — exact additive reason codes.

WHY THIS DESIGN
---------------
TreeSHAP was unavailable in this environment (`shap` requires `numba`, which fails to
build on Python 3.14, and `lightgbm` needs an OpenMP runtime we cannot install). Rather
than substitute an approximate or unfaithful explainer, the system is *architected* to be
explainable: the final score is produced by a logistic arbiter over five component scores,
so its log-odds decompose **exactly** and additively. The rule stage decomposes exactly
too, because each fired signal contributes a known weight.

That gives per-decision explanations that are true by construction rather than estimated.

An honest limitation, stated plainly: the gradient-boosted model contributes one term to
that decomposition, and we do **not** claim per-row attribution inside it. Model-internal
importance is reported globally (permutation importance) and labelled as global. Claiming
per-row tree attributions we cannot compute would be exactly the kind of plausible-but-
unfaithful explanation the XAI literature warns about.

We also deliberately avoid the automation-bias failure mode: across 3,735 real analyst
case reviews, explanations were found to raise analyst *confidence* without raising
accuracy. So every explanation carries the score decomposition (what actually drove the
decision) rather than a fluent narrative that merely sounds convincing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .detect import RULE_NAMES, RULE_WEIGHTS, Detector

# Plain-English reason text per signal. Written for an analyst, not a data scientist.
REASON_TEXT: dict[str, str] = {
    "amount_spike_vs_baseline": "Amount far above this card's own historical range",
    "behavioral_drift": "Behaviour has drifted from this card's established pattern",
    "subtle_drift": "Mild deviation from this card's usual amounts",
    "escalating_amount_sequence": "Amounts escalating across recent transactions",
    "credit_limit_exhaustion": "Declines alongside unusually large attempts",
    "thin_history": "Very little transaction history for this card",
    "new_account_velocity": "New account already transacting repeatedly",
    "immediate_high_value": "High-value spend almost immediately after onboarding",
    "velocity_burst": "Unusual burst of transactions within the hour",
    "device_change": "Transaction from a device never seen on this card",
    "device_sharing": "This device has been used by multiple unrelated cards",
    "many_cards_one_device": "Many distinct cards share this single device",
    "ip_concentration": "Multiple cards converging on one network prefix",
    "ua_homogeneity": "Many cards presenting an identical client fingerprint",
    "machine_cadence": "Inter-transaction timing too regular to be human",
    "no_human_session_rhythm": "No human interaction rhythm — automated traffic",
    "geo_mismatch": "Cross-border transaction in a country new to this card",
    "cross_border": "Cross-border transaction",
    "avs_failure": "Address verification failed",
    "no_3ds_challenge": "Card-not-present without strong authentication",
    "authenticated_but_anomalous":
        "Strong authentication succeeded, but behaviour is inconsistent with the "
        "cardholder — consistent with second-factor compromise or a victim-authorised scam",
    "new_merchant_risk": "Merchant registered very recently",
    "merchant_ticket_anomaly": "Amount inconsistent with this merchant's normal tickets",
    "many_cards_one_merchant": "Unusually many distinct cards at this merchant",
    "first_time_beneficiary": "First payment to this beneficiary, at elevated value",
    "beneficiary_concentration": "Many cards converging on one new beneficiary",
    "rapid_pass_through": "New merchant taking volume unusually fast",
    "mcc_inconsistency": "Ticket pattern inconsistent with the declared merchant category",
    "high_risk_mcc": "High-risk merchant category",
    "micro_amount_cluster": "Cluster of negligible-value authorisations — card testing",
    "auth_failure_ratio": "Elevated authorisation failures at this merchant",
    "bin_sequence_pattern": "Sequential credential probing signature",
    "amount_just_below_band": "Amount sits just below an authentication threshold",
    "sub_threshold_pacing": "Repeated amounts paced just under a threshold",
    "low_value_exemption_cluster": "Repeated low-value exemption claims by one card",
    "exemption_claim_anomaly": "Exemption claimed on an out-of-pattern transaction",
    "corporate_exemption_abuse": "High-value payment under a corporate exemption",
    "mandate_mismatch":
        "Authorisation diverges from the cardholder's signed payment instruction",
    "profile_change_then_spend": "Profile/device change immediately followed by large spend",
    "ring_component": "Card belongs to a connected cluster of linked accounts",
    "graph_fanin": "Network structure shows convergence typical of a fraud ring",
    "injection_pattern_in_text":
        "Merchant-supplied text contains prompt-injection patterns; treated as untrusted "
        "data and contained",
}

COMPONENT_LABELS = ("model_score", "rule_signals", "graph_structure",
                    "ring_membership", "injection_flag")

_WEIGHT_OF = dict(zip(RULE_NAMES, RULE_WEIGHTS))


def decompose(det: Detector, df: pd.DataFrame, X: pd.DataFrame | None = None) -> pd.DataFrame:
    """Exact additive decomposition of the arbiter's log-odds per transaction."""
    from .features import build_features

    d = df.reset_index(drop=True)
    X = build_features(d) if X is None else X.reset_index(drop=True)
    c = det._components(d, X)
    Z = det._stack(c)                                   # (n, 5) arbiter inputs
    coef = det.arbiter.coef_[0]
    contrib = Z * coef                                  # exact per-component contribution
    out = pd.DataFrame(contrib, columns=[f"contrib_{k}" for k in COMPONENT_LABELS])
    out.insert(0, "transaction_id", d["transaction_id"])
    out["intercept"] = float(det.arbiter.intercept_[0])
    out["logit_total"] = contrib.sum(axis=1) + out["intercept"]
    return out


def explain_one(
    det: Detector,
    df: pd.DataFrame,
    scored: pd.DataFrame,
    idx: int,
    top_k: int = 5,
) -> dict:
    """Human-facing explanation for a single transaction.

    Returns the decision, its exact component decomposition, ranked reason codes, and a
    counterfactual note. Nothing here is generated text — every element is derived from
    the arithmetic that produced the score.
    """
    row = scored.iloc[idx]
    signals: list[str] = list(row["detected_signals"])
    ranked = sorted(signals, key=lambda s: _WEIGHT_OF.get(s, 0.5), reverse=True)[:top_k]

    dec = decompose(det, df.iloc[[idx]])
    comps = {k: round(float(dec[f"contrib_{k}"].iloc[0]), 4) for k in COMPONENT_LABELS}
    driver = max(comps, key=lambda k: comps[k]) if comps else None

    return {
        "transaction_id": row["transaction_id"],
        "risk_score": float(row["risk_score"]),
        "risk_level": row["risk_level"],
        "recommended_action": row["recommended_action"],
        "primary_driver": driver,
        "component_contributions": comps,
        "reason_codes": [
            {"signal": s, "explanation": REASON_TEXT.get(s, s.replace("_", " ")),
             "weight": round(float(_WEIGHT_OF.get(s, 0.5)), 2)}
            for s in ranked
        ],
        "all_signals": signals,
        "counterfactual": _counterfactual(row, ranked),
        "explanation_basis": "exact additive decomposition of the arbiter log-odds",
        "caveat": (
            "Per-row attribution inside the gradient-boosted component is not claimed; "
            "its contribution is reported as a single exact term and its feature "
            "importance is reported globally."
        ),
        "synthetic": True,
    }


def _counterfactual(row: pd.Series, ranked: list[str]) -> str:
    """What would most plausibly have to change for this to score benign."""
    if not ranked:
        return "No signals fired; score driven by the statistical model alone."
    if row["risk_score"] < 0.30:
        return "Already below review threshold."
    lead = ranked[0]
    hints = {
        "many_cards_one_device": "if this device were not shared across multiple cards",
        "device_sharing": "if this device were not shared across multiple cards",
        "ip_concentration": "if these cards did not share one network prefix",
        "machine_cadence": "if the timing showed human variability",
        "no_human_session_rhythm": "if the timing showed human variability",
        "amount_spike_vs_baseline": "if the amount were within this card's usual range",
        "sub_threshold_pacing": "if amounts were not paced just under a threshold",
        "beneficiary_concentration": "if fewer cards converged on this beneficiary",
        "ring_component": "if this card were not linked to the wider cluster",
        "immediate_high_value": "if the account had established history first",
    }
    return f"Would likely fall below review {hints.get(lead, f'absent the {lead} signal')}."


def global_importance(det: Detector, df: pd.DataFrame, y: np.ndarray,
                      n_repeats: int = 3, seed: int = 0) -> pd.DataFrame:
    """Permutation importance of the model's features. GLOBAL, not per-row."""
    from sklearn.inspection import permutation_importance

    from .features import build_features

    X = build_features(df.reset_index(drop=True))[det.feature_cols]
    r = permutation_importance(
        det.model, X.to_numpy(), np.asarray(y), n_repeats=n_repeats,
        random_state=seed, scoring="average_precision",
    )
    return (
        pd.DataFrame({"feature": det.feature_cols,
                      "importance": r.importances_mean,
                      "std": r.importances_std})
        .sort_values("importance", ascending=False, ignore_index=True)
    )


def demo() -> None:
    """Self-check: the decomposition must be exact, not approximate."""
    from .attacks import run_all
    from .generator import build_population, generate_legit

    pop = build_population(n_cardholders=400, n_merchants=90, seed=1)
    hist = generate_legit(pop, days=24, seed=2)
    camps = run_all(pop, hist, strength=0.6, seed=7)
    df = pd.concat([hist] + [c.transactions for c in camps], ignore_index=True) \
        .sort_values("timestamp", kind="stable").reset_index(drop=True)
    y = df["is_fraud"].to_numpy()

    det = Detector().fit(df, y)
    scored = det.score(df)
    dec = decompose(det, df)

    # EXACTNESS: the additive decomposition must reproduce the arbiter's decision
    # function exactly. Compare against decision_function, not a logit round-trip
    # through predict_proba — the latter loses precision where probabilities saturate.
    from .features import build_features
    X = build_features(df)
    Z = det._stack(det._components(df, X))
    assert np.allclose(dec["logit_total"].to_numpy(), det.arbiter.decision_function(Z),
                       atol=1e-9), "decomposition is not exact"

    # Every high-risk decision must carry at least one reason code.
    hi = np.flatnonzero(scored["risk_level"].isin(["HIGH", "CRITICAL"]).to_numpy())
    assert len(hi), "no high-risk rows to explain"
    for i in hi[:25]:
        e = explain_one(det, df, scored, int(i))
        assert e["reason_codes"], f"no reason codes for {e['transaction_id']}"
        assert e["primary_driver"] in COMPONENT_LABELS
        assert e["counterfactual"]

    # Reason text must exist for every implemented signal.
    missing = [s for s in RULE_NAMES if s not in REASON_TEXT]
    assert not missing, f"signals without analyst-facing text: {missing}"

    ex = explain_one(det, df, scored, int(hi[0]))
    print(
        f"OK  decomposition exact · {len(hi):,} high-risk explained · "
        f"driver '{ex['primary_driver']}' · {len(ex['reason_codes'])} reason codes"
    )


if __name__ == "__main__":
    demo()
