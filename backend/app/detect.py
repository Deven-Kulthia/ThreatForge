"""Detection engine — a three-stage cascade with explicit arbitration.

ARCHITECTURE AND WHY
--------------------
    Stage 1  RULES     deterministic, named, auditable signals over causal features.
                       Cheap, instantly deployable, and the thing fraud teams actually
                       trust. Produces a rule score AND the named signals that fired.
    Stage 2  MODEL     HistGradientBoostingClassifier over 57 causal features.
                       Gradient-boosted trees, because the evidence is consistent that
                       they match or beat deep tabular models and tailored graph networks
                       on this kind of data (GADBench, NeurIPS 2023).
    Stage 3  GRAPH     neighbour/component structure over shared device, network prefix
                       and beneficiary merchant — computed ONLY for traffic that already
                       looks suspicious. This is what makes the cascade a cascade: the
                       expensive stage runs on a small fraction of the stream.
    ARBITER            a logistic regression over the three component scores, then
                       isotonic calibration. Small, transparent, and its coefficients are
                       exact — so the final score decomposes additively for explanation.

Deliberate choices, each with a reason:
  * No SMOTE. It degrades performance when the minority class is multimodal (fraud is,
    by definition — many distinct typologies), and applying it before the split is a
    documented leakage source. We use class weighting instead.
  * Calibration is not optional. Random undersampling can drive ECE from 0.008 to 0.395;
    without calibration a threshold like "block above 0.9" has no defensible meaning.
  * Every stage is fit on its own temporal slice, so the arbiter never sees the data the
    model was trained on and the calibrator never sees the arbiter's training data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from .features import build_features

# --------------------------------------------------------------------------------------
# Stage 1 — rule signals
# --------------------------------------------------------------------------------------
# Each rule maps a named detection signal to a vectorised predicate over the feature
# frame, plus a weight. Signal names deliberately match the `expected_detection_signals`
# declared by the attack taxonomy, which is what lets us measure whether an attack was
# caught FOR THE RIGHT REASON rather than merely caught.

Rule = tuple[str, object, float]

RULES: list[Rule] = [
    # --- amount / baseline deviation ---
    ("amount_spike_vs_baseline", lambda f: (f.card_amt_z > 4) | (f.card_amt_ratio > 6), 1.0),
    ("behavioral_drift", lambda f: (f.card_amt_z > 2.5) | (f.card_new_device > 0), 0.6),
    ("subtle_drift", lambda f: (f.card_amt_z > 1.0) & (f.card_amt_z <= 2.5), 0.25),
    ("escalating_amount_sequence", lambda f: (f.card_amt_ratio > 2) & (f.card_txn_7d >= 3), 0.5),
    ("credit_limit_exhaustion", lambda f: (f.auth_declined > 0) & (f.card_amt_ratio > 3), 0.7),
    # --- account age / history ---
    ("thin_history", lambda f: f.card_history_len < 3, 0.4),
    ("new_account_velocity", lambda f: (f.card_history_len < 5) & (f.card_txn_24h >= 2), 0.6),
    ("immediate_high_value", lambda f: (f.card_history_len <= 2) & (f.amount > 300), 1.0),
    # --- velocity ---
    ("velocity_burst", lambda f: f.card_txn_1h >= 4, 0.8),
    # --- device / network / agent infrastructure ---
    ("device_change", lambda f: (f.card_new_device > 0) & (f.card_history_len > 3), 0.5),
    ("device_sharing", lambda f: f.dev_prior_cards >= 3, 0.9),
    ("many_cards_one_device", lambda f: f.dev_prior_cards >= 8, 1.3),
    ("ip_concentration", lambda f: f.ip_prior_cards >= 5, 0.9),
    ("ua_homogeneity", lambda f: f.ua_prior_cards >= 8, 0.7),
    ("machine_cadence", lambda f: (f.dev_cadence_std >= 0) & (f.dev_cadence_std < 2.0), 1.0),
    ("no_human_session_rhythm",
     lambda f: (f.dev_cadence_std >= 0) & (f.dev_cadence_std < 0.5), 1.1),
    # --- geography ---
    ("geo_mismatch", lambda f: (f.cross_border > 0) & (f.card_new_country > 0), 0.7),
    ("cross_border", lambda f: f.cross_border > 0, 0.2),
    # --- verification posture ---
    ("avs_failure", lambda f: f.avs_fail > 0, 0.5),
    ("no_3ds_challenge",
     lambda f: (f.threeds_na > 0) & (f.card_present == 0) & (f.is_recurring == 0), 0.4),
    # The dangerous case: strong authentication genuinely succeeded, yet behaviour is off.
    # This is the signature of OTP interception and of victim-authorised scams.
    ("authenticated_but_anomalous",
     lambda f: (f.threeds_authenticated > 0) & ((f.card_amt_z > 3) | (f.card_new_device > 0)), 1.2),
    # --- merchant ---
    ("new_merchant_risk", lambda f: f.merchant_is_new > 0, 0.6),
    ("merchant_ticket_anomaly", lambda f: (f.mch_amt_z > 3) | (f.mch_amt_ratio > 4), 0.7),
    ("many_cards_one_merchant", lambda f: f.mch_prior_cards >= 10, 0.8),
    ("first_time_beneficiary", lambda f: (f.card_new_merchant > 0) & (f.card_amt_ratio > 3), 1.0),
    ("beneficiary_concentration",
     lambda f: (f.mch_prior_cards >= 8) & (f.merchant_is_new > 0), 1.1),
    ("rapid_pass_through",
     lambda f: (f.merchant_is_new > 0) & (f.mch_txn_1h >= 5), 0.9),
    ("mcc_inconsistency",
     lambda f: (f.high_risk_mcc == 0) & (f.merchant_is_new > 0) & (f.mch_amt_z > 2), 0.7),
    ("high_risk_mcc", lambda f: f.high_risk_mcc > 0, 0.3),
    # --- enumeration ---
    ("micro_amount_cluster", lambda f: (f.micro_amount > 0) & (f.mch_txn_1h >= 5), 1.2),
    ("auth_failure_ratio", lambda f: (f.auth_declined > 0) & (f.mch_txn_1h >= 5), 1.0),
    ("bin_sequence_pattern",
     lambda f: (f.card_history_len == 0) & (f.micro_amount > 0) & (f.ip_prior_cards >= 5), 1.3),
    # --- exemption / threshold gaming (PSD2 RTS Art. 11-18 abuse surface) ---
    ("amount_just_below_band", lambda f: f.band_proximity < 0.05, 0.6),
    ("sub_threshold_pacing",
     lambda f: (f.band_proximity < 0.05) & (f.card_txn_24h >= 3), 1.0),
    ("low_value_exemption_cluster",
     lambda f: (f.sca_low_value > 0) & (f.card_txn_24h >= 5), 1.1),
    ("exemption_claim_anomaly",
     lambda f: ((f.sca_tra > 0) | (f.sca_corporate > 0)) & (f.card_amt_z > 2), 0.8),
    ("corporate_exemption_abuse", lambda f: (f.sca_corporate > 0) & (f.amount > 2000), 1.0),
    ("mandate_mismatch",
     lambda f: (f.band_proximity < 0.05) & (f.dev_cadence_std >= 0) & (f.dev_cadence_std < 2)
     & (f.network_token > 0), 1.2),
    ("profile_change_then_spend",
     lambda f: (f.card_new_device > 0) & (f.card_amt_ratio > 5), 1.1),
]

# Signals declared by the taxonomy that we do NOT implement, and why. Stated explicitly
# so per-signal recall is read honestly rather than looking like a silent miss.
UNIMPLEMENTED_SIGNALS: dict[str, str] = {
    "session_duress_pattern": "requires session/interaction telemetry, outside the auth schema",
    "refund_ratio_anomaly": "requires credit/refund messages, outside the auth schema",
    "post_delivery_dispute": "requires dispute lifecycle data, outside the auth schema",
    "repeat_claimant_pattern": "requires dispute lifecycle data, outside the auth schema",
    "synchronised_timing": "covered in practice by ring_component + machine_cadence",
    "graph_fanin": "emitted by the graph stage, not the rule stage",
    "ring_component": "emitted by the graph stage, not the rule stage",
    "injection_pattern_in_text": "emitted by the text-safety stage",
}

RULE_NAMES: list[str] = [r[0] for r in RULES]
RULE_WEIGHTS = np.array([r[2] for r in RULES], dtype=float)

# --------------------------------------------------------------------------------------
# Prompt-injection containment (OWASP LLM01:2025)
# --------------------------------------------------------------------------------------
# Merchant-controlled free text is untrusted input. It is treated as DATA, never as
# instructions, and is pattern-screened before it can reach any downstream model that
# reads transaction text. Containment is structural: the text is never concatenated into
# a prompt, and a match raises a signal rather than altering control flow.

_INJECTION_PATTERNS = re.compile(
    r"(?:ignore\s+(?:all\s+|previous\s+|prior\s+)*instruction"
    r"|disregard\s+(?:prior|previous|all)"
    r"|system\s*:"
    r"|assistant\s*:"
    r"|</?(?:data|system|prompt)>"
    r"|risk_score\s*="
    r"|mark\s+this\s+transaction"
    r"|treat\s+\w+\s+as\s+trusted"
    r"|approve\s+this\s+payment)",
    re.IGNORECASE,
)


def screen_text(values: pd.Series) -> np.ndarray:
    """Flag merchant-controlled text carrying prompt-injection patterns."""
    return values.fillna("").astype(str).str.contains(_INJECTION_PATTERNS).to_numpy()


# --------------------------------------------------------------------------------------
# Stage 3 — graph structure
# --------------------------------------------------------------------------------------


def graph_scores(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Component-level risk over shared device / network / beneficiary structure.

    Returns (score in [0,1], ring flag). Fraud rings are invisible per transaction and
    obvious as a graph: many distinct cards bound together by shared infrastructure or
    converging on the same new beneficiary.
    """
    n = len(df)
    if n == 0:
        return np.zeros(0), np.zeros(0, dtype=bool)

    g = nx.Graph()
    cards = df["card_token"].to_numpy()
    for col, prefix in (("device_id", "d:"), ("ip_prefix", "n:"), ("merchant_id", "m:")):
        vals = df[col].to_numpy()
        for c, v in zip(cards, vals):
            g.add_edge(f"c:{c}", f"{prefix}{v}")

    # Cards per component — the quantity that actually indicates a ring.
    card_of_comp: dict[str, int] = {}
    comp_cards: dict[int, int] = {}
    for i, comp in enumerate(nx.connected_components(g)):
        k = sum(1 for x in comp if x.startswith("c:"))
        comp_cards[i] = k
        for x in comp:
            card_of_comp[x] = i

    sizes = np.array([comp_cards.get(card_of_comp.get(f"c:{c}", -1), 1) for c in cards],
                     dtype=float)
    # Saturating transform: 1 card is innocuous, 10+ linked cards is a ring.
    score = np.clip((sizes - 1.0) / 9.0, 0.0, 1.0)
    return score, sizes >= 5


# --------------------------------------------------------------------------------------
# Detector
# --------------------------------------------------------------------------------------

RISK_BANDS = ((0.85, "CRITICAL", "BLOCK"), (0.60, "HIGH", "STEP_UP"),
              (0.30, "MEDIUM", "REVIEW"), (0.0, "LOW", "ALLOW"))

# Fraction of traffic allowed to reach the expensive graph stage. An explicit compute
# budget is how production cascades actually work — a fixed absolute threshold drifts
# with score distribution and silently degenerates into "run everything".
GRAPH_GATE_FRACTION = 0.20


@dataclass
class Detector:
    model: HistGradientBoostingClassifier | None = None
    arbiter: LogisticRegression | None = None
    calibrator: IsotonicRegression | None = None
    feature_cols: list[str] = field(default_factory=list)
    gate_fraction: float = GRAPH_GATE_FRACTION

    # ---------- component scores ----------
    @staticmethod
    def rule_matrix(X: pd.DataFrame) -> np.ndarray:
        """Boolean matrix of fired rules, shape (n_rows, n_rules)."""
        return np.column_stack([pred(X).to_numpy().astype(bool) for _, pred, _ in RULES])

    @classmethod
    def rule_score(cls, M: np.ndarray) -> np.ndarray:
        """Weighted rule score, squashed into [0,1)."""
        raw = M @ RULE_WEIGHTS
        return 1.0 - np.exp(-raw / 3.0)          # saturating: many weak signals ≠ certainty

    def _components(self, df: pd.DataFrame, X: pd.DataFrame) -> dict[str, np.ndarray]:
        M = self.rule_matrix(X)
        s_rules = self.rule_score(M)
        p_model = (
            self.model.predict_proba(X[self.feature_cols].to_numpy())[:, 1]
            if self.model is not None else np.zeros(len(X))
        )
        injected = screen_text(df["merchant_name"])

        # Cascade gate: expensive graph work only on the riskiest slice of traffic,
        # sized by an explicit compute budget.
        s_graph = np.zeros(len(X))
        rings = np.zeros(len(X), dtype=bool)
        pre = np.maximum(p_model, s_rules)
        k = max(1, int(round(len(pre) * self.gate_fraction)))
        sel = np.argsort(-pre)[:k] if len(pre) else np.array([], dtype=int)
        gated = np.zeros(len(X), dtype=bool)
        gated[sel] = True
        if len(sel):
            gs, rg = graph_scores(df.iloc[sel])
            s_graph[sel] = gs
            rings[sel] = rg
        return {"p_model": p_model, "s_rules": s_rules, "s_graph": s_graph,
                "rules": M, "rings": rings, "injected": injected,
                "graph_evaluated": gated}

    @staticmethod
    def _stack(c: dict[str, np.ndarray]) -> np.ndarray:
        """Arbiter input. The model probability enters as a logit so the arbiter is
        combining comparable log-odds quantities rather than a probability and two scores."""
        p = np.clip(c["p_model"], 1e-6, 1 - 1e-6)
        return np.column_stack([np.log(p / (1 - p)), c["s_rules"], c["s_graph"],
                                c["rings"].astype(float), c["injected"].astype(float)])

    # ---------- training ----------
    def fit(self, df: pd.DataFrame, y: np.ndarray) -> "Detector":
        """Fit on three disjoint temporal slices: model, arbiter, calibrator.

        Temporal (not random) splitting is essential — random splits let the model train
        on events that occur after the ones it is scored on.
        """
        d = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
        y = np.asarray(y)[np.argsort(
            pd.to_datetime(df["timestamp"]).to_numpy(), kind="stable")]
        X = build_features(d)
        self.feature_cols = list(X.columns)

        n = len(d)
        a, b = int(n * 0.60), int(n * 0.80)
        if y[:a].sum() < 2 or y[a:b].sum() < 2:
            raise ValueError("insufficient positives per temporal slice to fit safely")

        # Stage 2 — model. Class weighting, never resampling.
        self.model = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.08, max_leaf_nodes=31,
            min_samples_leaf=20, l2_regularization=1.0,
            class_weight="balanced", early_stopping=False, random_state=0,
        ).fit(X.iloc[:a].to_numpy(), y[:a])

        # Arbiter on slice B.
        cb = self._components(d.iloc[a:b], X.iloc[a:b])
        self.arbiter = LogisticRegression(max_iter=2000, class_weight="balanced").fit(
            self._stack(cb), y[a:b])

        # Calibrator on slice C — never seen by model or arbiter.
        cc = self._components(d.iloc[b:], X.iloc[b:])
        raw = self.arbiter.predict_proba(self._stack(cc))[:, 1]
        self.calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self.calibrator.fit(raw, y[b:])
        return self

    # ---------- scoring ----------
    def score(self, df: pd.DataFrame, X: pd.DataFrame | None = None) -> pd.DataFrame:
        """Score transactions. Returns risk, band, action, components and fired signals."""
        d = df.reset_index(drop=True)
        X = build_features(d) if X is None else X.reset_index(drop=True)
        c = self._components(d, X)
        raw = self.arbiter.predict_proba(self._stack(c))[:, 1]
        risk = self.calibrator.predict(raw) if self.calibrator is not None else raw

        bands = np.empty(len(d), dtype=object)
        actions = np.empty(len(d), dtype=object)
        for lo, name, act in RISK_BANDS:
            m = (risk >= lo) & (bands == None)          # noqa: E711 — object-array mask
            bands[m], actions[m] = name, act

        M = c["rules"]
        signals = [
            [RULE_NAMES[j] for j in np.flatnonzero(M[i])]
            + (["ring_component", "graph_fanin"] if c["rings"][i] else [])
            + (["injection_pattern_in_text"] if c["injected"][i] else [])
            for i in range(len(d))
        ]

        return pd.DataFrame({
            "transaction_id": d["transaction_id"],
            "risk_score": np.round(risk, 4),
            "risk_level": bands,
            "recommended_action": actions,
            "p_model": np.round(c["p_model"], 4),
            "s_rules": np.round(c["s_rules"], 4),
            "s_graph": np.round(c["s_graph"], 4),
            "graph_evaluated": c["graph_evaluated"],
            "injection_detected": c["injected"],
            "detected_signals": signals,
            "n_signals": [len(s) for s in signals],
        })


def demo() -> None:
    """Self-check: the detector must train, separate, calibrate and stay auditable."""
    from sklearn.metrics import average_precision_score

    from .attacks import run_all
    from .generator import build_population, generate_legit

    pop = build_population(n_cardholders=600, n_merchants=120, seed=1)
    hist = generate_legit(pop, days=30, seed=2)
    camps = run_all(pop, hist, strength=0.6, seed=11)
    atk = pd.concat([c.transactions for c in camps], ignore_index=True)
    df = pd.concat([hist, atk], ignore_index=True).sort_values(
        "timestamp", kind="stable").reset_index(drop=True)
    y = df["is_fraud"].to_numpy()

    det = Detector().fit(df, y)
    out = det.score(df)

    ap = average_precision_score(y, out["risk_score"].to_numpy())
    assert ap > 0.5, f"detector is not learning: PR-AUC {ap:.3f}"
    assert out["risk_score"].between(0, 1).all(), "risk score out of range"
    # Every flagged transaction must carry at least one named reason.
    flagged = out[out["risk_level"].isin(["HIGH", "CRITICAL"])]
    assert (flagged["n_signals"] > 0).all(), "flagged rows without any named signal"
    # The cascade must actually gate: the graph stage should see a minority of traffic.
    share = out["graph_evaluated"].mean()
    assert share <= 0.25, f"cascade not gating, graph ran on {share:.0%}"
    # Prompt injection must be caught.
    inj = df["attack_type"] == "AGENT_PROMPT_INJECTION"
    assert out.loc[inj.to_numpy(), "injection_detected"].all(), "injection payload missed"

    print(
        f"OK  PR-AUC {ap:.3f} · {len(RULES)} rules · graph stage on "
        f"{share:.1%} of traffic · {len(df):,} txns · fraud {y.mean():.2%}"
    )


if __name__ == "__main__":
    demo()
