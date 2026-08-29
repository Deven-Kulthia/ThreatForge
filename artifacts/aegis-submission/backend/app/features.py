"""Feature engineering for payment fraud detection.

CAUSALITY GUARANTEE
-------------------
Every feature in this module is computed from *strictly prior* events for the entity in
question. Window statistics use `searchsorted` over sorted timestamps and exclude the
current row, and running moments use shifted cumulative sums. There is no `.mean()` over
a whole column, no target encoding, and no future information anywhere.

This matters more than it sounds: the single most common defect in published fraud-ML work
is leakage that inflates results (e.g. resampling before the train/test split), and a
detector trained on leaked features looks excellent offline and fails in production.

The feature families are chosen from what the evidence says actually works:
  * velocity over multiple horizons (the workhorse of production systems)
  * deviation from the entity's OWN baseline, not a population baseline — the only way to
    catch account takeover and scam cases where credentials are genuine
  * neighbour aggregation over shared device / IP / merchant, which GADBench found
    outperforms bespoke graph neural networks when fed to a tree ensemble
  * verification-result and exemption flags, which is where payments realism lives
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .schema import HIGH_RISK_MCCS

HOUR = 3_600 * 1_000_000_000          # nanoseconds
DAY = 24 * HOUR
WEEK = 7 * DAY


# --------------------------------------------------------------------------------------
# Primitives — all strictly causal
# --------------------------------------------------------------------------------------


def _window(ts: np.ndarray, vals: np.ndarray, span: int) -> tuple[np.ndarray, np.ndarray]:
    """Count and sum of prior events within `span` nanoseconds. Excludes the current row."""
    left = np.searchsorted(ts, ts - span, side="left")
    pos = np.arange(len(ts))
    counts = (pos - left).astype(np.float64)
    csum = np.concatenate(([0.0], np.cumsum(vals)))
    sums = csum[pos] - csum[left]
    return counts, sums


def _safe_div(num: np.ndarray, den: np.ndarray, default: float = 1.0) -> np.ndarray:
    """Divide only where the denominator is positive. `np.where` would evaluate both
    branches and emit divide-by-zero warnings, so do the masking inside the divide."""
    out = np.full(len(den), float(default))
    return np.divide(num, den, out=out, where=den > 0)


def _groups(df: pd.DataFrame, key: str) -> dict[object, np.ndarray]:
    """Row positions per entity. df must already be sorted by timestamp."""
    return {k: np.sort(v) for k, v in df.groupby(key, sort=False).indices.items()}


def _velocity(df: pd.DataFrame, key: str, span: int, ts_ns: np.ndarray,
              amt: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    counts = np.zeros(len(df))
    sums = np.zeros(len(df))
    for idx in _groups(df, key).values():
        c, s = _window(ts_ns[idx], amt[idx], span)
        counts[idx] = c
        sums[idx] = s
    return counts, sums


def _prior_moments(df: pd.DataFrame, key: str, ts_ns: np.ndarray,
                   amt: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Running count / mean / std of an entity's prior amounts (self excluded)."""
    n = len(df)
    cnt = np.zeros(n)
    mean = np.zeros(n)
    std = np.zeros(n)
    for idx in _groups(df, key).values():
        v = amt[idx]
        pos = np.arange(len(idx), dtype=np.float64)
        cs = np.concatenate(([0.0], np.cumsum(v)))[: len(idx)]
        cq = np.concatenate(([0.0], np.cumsum(v * v)))[: len(idx)]
        with np.errstate(invalid="ignore", divide="ignore"):
            m = np.where(pos > 0, cs / np.maximum(pos, 1), 0.0)
            var = np.where(pos > 1, cq / np.maximum(pos, 1) - m * m, 0.0)
        cnt[idx] = pos
        mean[idx] = m
        std[idx] = np.sqrt(np.maximum(var, 0.0))
    return cnt, mean, std


def _prior_distinct(df: pd.DataFrame, key: str, target: str) -> np.ndarray:
    """Number of distinct `target` values this `key` had seen BEFORE the current row.

    This is the neighbour-aggregation signal that exposes shared-infrastructure attacks:
    one device touching many cards, or one merchant drawing many unrelated cards.
    """
    out = np.zeros(len(df))
    tgt = df[target].to_numpy()
    for idx in _groups(df, key).values():
        seen: set = set()
        for j in idx:
            out[j] = len(seen)
            seen.add(tgt[j])
    return out


def _is_first_seen(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    """1.0 the first time this combination appears for the entity, else 0.0."""
    return (~df.duplicated(subset=cols, keep="first")).to_numpy().astype(np.float64)


def _prev_gap(df: pd.DataFrame, key: str, ts_ns: np.ndarray) -> np.ndarray:
    """Seconds since this entity's previous event. -1 when there is no previous event."""
    out = np.full(len(df), -1.0)
    for idx in _groups(df, key).values():
        t = ts_ns[idx]
        if len(t) > 1:
            out[idx[1:]] = np.diff(t) / 1e9
    return out


def _gap_regularity(df: pd.DataFrame, key: str, ts_ns: np.ndarray, k: int = 5) -> np.ndarray:
    """Std-dev of the last `k` inter-arrival gaps (seconds).

    Near-zero means machine-generated cadence — the clearest tell for automated agents
    and enumeration. Returns -1 when there is insufficient history.
    """
    out = np.full(len(df), -1.0)
    for idx in _groups(df, key).values():
        t = ts_ns[idx]
        if len(t) < 3:
            continue
        gaps = np.diff(t) / 1e9
        for i in range(2, len(idx)):
            w = gaps[max(0, i - 1 - k):i - 1 + 1]
            if len(w) >= 2:
                out[idx[i]] = float(np.std(w))
    return out


# --------------------------------------------------------------------------------------
# Feature builder
# --------------------------------------------------------------------------------------

# PSD2 RTS Annex reference exemption bands (EUR). Attackers who game banded logic sit
# just underneath these, so proximity-from-below is itself a signal.
BANDS = (30.0, 100.0, 250.0, 500.0)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the causal feature matrix. Input must contain the observable schema fields."""
    d = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
    ts = pd.to_datetime(d["timestamp"])
    ts_ns = ts.astype("int64").to_numpy()
    amt = d["amount"].astype(float).to_numpy()

    f = pd.DataFrame(index=d.index)

    # --- amount shape ---
    f["amount"] = amt
    f["log_amount"] = np.log1p(amt)
    f["micro_amount"] = (amt < 3.0).astype(float)
    f["round_amount"] = ((amt % 50.0 == 0) | (amt % 100.0 == 0)).astype(float)
    # Distance below the nearest exemption band, as a fraction of that band.
    below = np.full(len(d), 1.0)
    for b in BANDS:
        prox = np.where((amt <= b) & (amt > b * 0.9), (b - amt) / b, 1.0)
        below = np.minimum(below, prox)
    f["band_proximity"] = below                     # ~0 ⇒ sitting just under a threshold

    # --- temporal ---
    f["hour"] = ts.dt.hour.to_numpy().astype(float)
    f["is_night"] = ts.dt.hour.isin([0, 1, 2, 3, 4, 5]).to_numpy().astype(float)
    f["dow"] = ts.dt.dayofweek.to_numpy().astype(float)
    f["is_weekend"] = (ts.dt.dayofweek >= 5).to_numpy().astype(float)

    # --- presentation / channel ---
    f["card_present"] = d["card_present"].astype(float)
    f["is_recurring"] = d["is_recurring"].astype(float)
    f["cross_border"] = d["cross_border"].astype(float)
    f["network_token"] = d["network_token_used"].astype(float)
    em = d["entry_mode"].astype(str)
    f["entry_magstripe"] = (em == "MAGSTRIPE").astype(float)
    f["entry_keyed"] = (em == "ECOM_KEYED").astype(float)
    f["entry_cof"] = (em == "CREDENTIAL_ON_FILE").astype(float)

    # --- merchant risk ---
    f["high_risk_mcc"] = d["mcc"].isin(HIGH_RISK_MCCS).astype(float)
    age = d["merchant_age_days"].astype(float)
    f["merchant_age_days"] = age
    f["merchant_is_new"] = (age < 30).astype(float)
    f["log_merchant_age"] = np.log1p(age)

    # --- verification results (payments realism lives here) ---
    avs = d["avs_result"].astype(str)
    f["avs_fail"] = avs.isin(["N", "U"]).astype(float)
    f["avs_partial"] = avs.isin(["Z", "A"]).astype(float)
    cvv = d["cvv_result"].astype(str)
    f["cvv_fail"] = (cvv == "N").astype(float)
    f["cvv_absent"] = cvv.isin(["S", "P"]).astype(float)
    tds = d["three_ds_status"].astype(str)
    f["threeds_authenticated"] = (tds == "Y").astype(float)
    f["threeds_failed"] = tds.isin(["N", "U"]).astype(float)
    f["threeds_na"] = (tds == "X").astype(float)
    sca = d["sca_exemption"].astype(str)
    f["sca_low_value"] = (sca == "LOW_VALUE").astype(float)
    f["sca_tra"] = (sca == "TRA").astype(float)
    f["sca_corporate"] = (sca == "CORPORATE").astype(float)
    f["auth_declined"] = (d["auth_response"].astype(str) != "00").astype(float)

    # --- card velocity ---
    for span, tag in ((HOUR, "1h"), (DAY, "24h"), (WEEK, "7d")):
        c, s = _velocity(d, "card_token", span, ts_ns, amt)
        f[f"card_txn_{tag}"] = c
        f[f"card_amt_{tag}"] = s

    # --- card behaviour vs its OWN baseline ---
    cnt, mean, std = _prior_moments(d, "card_token", ts_ns, amt)
    f["card_history_len"] = cnt
    f["card_amt_ratio"] = _safe_div(amt, mean, 1.0)
    f["card_amt_z"] = _safe_div(amt - mean, std, 0.0)
    f["card_secs_since_prev"] = _prev_gap(d, "card_token", ts_ns)
    f["card_cadence_std"] = _gap_regularity(d, "card_token", ts_ns)
    f["card_new_merchant"] = _is_first_seen(d, ["card_token", "merchant_id"])
    f["card_new_device"] = _is_first_seen(d, ["card_token", "device_id"])
    f["card_new_country"] = _is_first_seen(d, ["card_token", "merchant_country"])
    f["card_prior_devices"] = _prior_distinct(d, "card_token", "device_id")

    # --- device: neighbour aggregation (shared-infrastructure attacks) ---
    c, _ = _velocity(d, "device_id", HOUR, ts_ns, amt)
    f["dev_txn_1h"] = c
    c, _ = _velocity(d, "device_id", DAY, ts_ns, amt)
    f["dev_txn_24h"] = c
    f["dev_prior_cards"] = _prior_distinct(d, "device_id", "card_token")
    f["dev_cadence_std"] = _gap_regularity(d, "device_id", ts_ns)

    # --- network prefix ---
    c, _ = _velocity(d, "ip_prefix", DAY, ts_ns, amt)
    f["ip_txn_24h"] = c
    f["ip_prior_cards"] = _prior_distinct(d, "ip_prefix", "card_token")
    f["ua_prior_cards"] = _prior_distinct(d, "user_agent_hash", "card_token")

    # --- merchant: fan-in and ticket anomaly ---
    c, _ = _velocity(d, "merchant_id", HOUR, ts_ns, amt)
    f["mch_txn_1h"] = c
    f["mch_prior_cards"] = _prior_distinct(d, "merchant_id", "card_token")
    _, m_mean, m_std = _prior_moments(d, "merchant_id", ts_ns, amt)
    f["mch_amt_ratio"] = _safe_div(amt, m_mean, 1.0)
    f["mch_amt_z"] = _safe_div(amt - m_mean, m_std, 0.0)

    return f.astype(np.float64).replace([np.inf, -np.inf], 0.0).fillna(0.0)


def feature_names(df_features: pd.DataFrame) -> list[str]:
    return list(df_features.columns)


def demo() -> None:
    """Self-check: the causality guarantee must actually hold."""
    from .attacks import run_attack
    from .generator import build_population, generate_legit

    pop = build_population(n_cardholders=250, n_merchants=70, seed=1)
    hist = generate_legit(pop, days=14, seed=2)
    camp = run_attack("ATO_CREDENTIAL_STUFF", pop, hist, strength=0.8, seed=3)
    df = pd.concat([hist, camp.transactions], ignore_index=True)

    X = build_features(df)
    assert len(X) == len(df), "row count changed"
    assert X.notna().all().all(), "NaNs leaked into features"
    assert np.isfinite(X.to_numpy()).all(), "non-finite features"

    # The first event for any card can have no history.
    d = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
    first = ~d.duplicated("card_token", keep="first")
    assert (X.loc[first.to_numpy(), "card_txn_24h"] == 0).all(), "history leaked to first event"
    assert (X.loc[first.to_numpy(), "card_secs_since_prev"] == -1).all(), "gap leaked"

    # CAUSALITY: recomputing on a time-truncated prefix must reproduce prefix features
    # exactly. If any feature peeked at the future, this fails.
    cut = int(len(d) * 0.6)
    X_pref = build_features(d.iloc[:cut])
    pd.testing.assert_frame_equal(
        X.iloc[:cut].reset_index(drop=True), X_pref.reset_index(drop=True),
        check_exact=False, atol=1e-9,
    )

    # The credential-stuffing campaign must light up device fan-in.
    atk = d["is_fraud"].to_numpy() == 1
    assert X.loc[atk, "dev_prior_cards"].max() > X.loc[~atk, "dev_prior_cards"].max(), \
        "device fan-in does not separate the shared-infrastructure attack"

    print(f"OK  {X.shape[1]} features · {len(X):,} rows · causality verified on prefix")


if __name__ == "__main__":
    demo()
