"""Synthetic payment traffic generator.

Produces legitimate authorization traffic for a synthetic population of cardholders,
merchants and devices. Fraud is NOT produced here — attack campaigns are layered on
top by `attacks.py`, so that legitimate behaviour and adversarial behaviour come from
independent code paths and the detector cannot exploit a generation artefact.

Design goals (competition criterion 2 — "fidelity of attacks in simulation"):
  * Per-cardholder stable habits: home country, spend scale, MCC affinity, primary device.
  * Diurnal + weekly rhythm rather than uniform time sampling.
  * MCC-conditioned ticket sizes and card-present bias.
  * Verification fields (AVS/CVV/3DS/SCA) that behave the way a real acquirer would set them.
  * Deterministic under a seed, so every reported metric is reproducible.

Fraud-rate anchors: PSD2 RTS Annex reference remote-card fraud rates are 0.01% / 0.06% /
0.13% for ETV bands EUR 500 / 250 / 100 (i.e. ~1-13 basis points). Stripe reports fraud at
roughly 1 in 1,000 payments. We therefore target a base rate in the 0.1-0.5% band rather
than the inflated rates common in public fraud datasets.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .schema import (
    COUNTRIES,
    CURRENCY_BY_COUNTRY,
    MCC_CATALOG,
    TRANSACTION_FIELDS,
    AuthResponse,
    AvsResult,
    Channel,
    CvvResult,
    EntryMode,
    ScaExemption,
    ThreeDsStatus,
)

# Relative transaction intensity by hour of day (local). Two peaks: lunch and evening.
DIURNAL_WEIGHTS = np.array(
    [0.4, 0.25, 0.15, 0.1, 0.1, 0.2, 0.5, 1.0, 1.6, 1.8, 1.9, 2.2,
     2.6, 2.3, 1.9, 1.8, 2.0, 2.4, 2.8, 2.7, 2.2, 1.7, 1.1, 0.7]
)
DIURNAL_P = DIURNAL_WEIGHTS / DIURNAL_WEIGHTS.sum()

# Sat/Sun carry more discretionary spend.
WEEKDAY_MULT = np.array([1.0, 0.98, 1.0, 1.05, 1.25, 1.4, 1.15])


@dataclass(frozen=True)
class Population:
    """Static synthetic entities. Reused across runs so entity history is coherent."""

    cards: pd.DataFrame
    merchants: pd.DataFrame

    @property
    def n_cards(self) -> int:
        return len(self.cards)

    @property
    def n_merchants(self) -> int:
        return len(self.merchants)


def build_population(
    n_cardholders: int = 2_000,
    n_merchants: int = 400,
    seed: int = 7,
) -> Population:
    """Create the synthetic cardholder and merchant populations."""
    rng = np.random.default_rng(seed)

    # --- cardholders ---
    country_codes = [c for c, _ in COUNTRIES]
    country_p = np.array([w for _, w in COUNTRIES], dtype=float)
    country_p /= country_p.sum()
    home = rng.choice(country_codes, size=n_cardholders, p=country_p)

    # Affluence multiplier is lognormal: most cardholders cluster, a few spend heavily.
    affluence = rng.lognormal(mean=0.0, sigma=0.55, size=n_cardholders)
    # Daily transaction rate: most cardholders transact 0.5-4x/day.
    daily_rate = np.clip(rng.gamma(shape=2.2, scale=0.65, size=n_cardholders), 0.15, 8.0)

    mcc_codes = [m[0] for m in MCC_CATALOG]
    # Everyday categories are far likelier to be part of a cardholder's habitual set than
    # niche/digital ones, so weight the affinity draw by card-present bias too. Without
    # this the channel mix flattens to unrealistically card-not-present-heavy traffic.
    mcc_w = np.array([0.30 + 2.5 * m[4] for m in MCC_CATALOG])
    mcc_p = mcc_w / mcc_w.sum()
    # Each cardholder prefers a handful of categories; the rest are occasional.
    n_pref = rng.integers(3, 7, size=n_cardholders)
    preferred = [
        rng.choice(mcc_codes, size=k, replace=False, p=mcc_p) for k in n_pref
    ]

    cards = pd.DataFrame(
        {
            "card_token": [f"tok_{i:07d}" for i in range(n_cardholders)],
            "account_id": [f"acct_{i:07d}" for i in range(n_cardholders)],
            "issuer_country": home,
            "currency": [CURRENCY_BY_COUNTRY[c] for c in home],
            "affluence": affluence,
            "daily_rate": daily_rate,
            "preferred_mccs": preferred,
            # Primary device + network. Stability of these is a core legitimacy signal.
            "primary_device": [f"dev_{i:07d}" for i in range(n_cardholders)],
            "primary_ip_prefix": [
                f"{rng.integers(11, 223)}.{rng.integers(0, 255)}.{rng.integers(0, 255)}.0/24"
                for _ in range(n_cardholders)
            ],
            "ua_hash": [f"ua_{rng.integers(0, 9999):04d}" for _ in range(n_cardholders)],
            # Propensity to shop online at all.
            "ecom_propensity": rng.beta(2.5, 3.0, size=n_cardholders),
            # Propensity to transact abroad.
            "travel_propensity": rng.beta(1.2, 12.0, size=n_cardholders),
        }
    )

    # --- merchants ---
    mcc_idx = rng.integers(0, len(MCC_CATALOG), size=n_merchants)
    m_countries = rng.choice(country_codes, size=n_merchants, p=country_p)
    merchants = pd.DataFrame(
        {
            "merchant_id": [f"mch_{i:06d}" for i in range(n_merchants)],
            "merchant_name": [
                f"{MCC_CATALOG[j][1].split('/')[0].strip().replace(' ', '')[:14]}-{i:04d}"
                for i, j in enumerate(mcc_idx)
            ],
            "mcc": [MCC_CATALOG[j][0] for j in mcc_idx],
            "typical_ticket": [MCC_CATALOG[j][2] for j in mcc_idx],
            "is_high_risk": [MCC_CATALOG[j][3] for j in mcc_idx],
            "cp_bias": [MCC_CATALOG[j][4] for j in mcc_idx],
            "merchant_country": m_countries,
            # Merchant tenure matters: brand-new merchants are a laundering signal.
            "merchant_age_days": np.clip(
                rng.gamma(shape=2.0, scale=420.0, size=n_merchants), 3, 5000
            ).astype(int),
            # Popularity governs how often a merchant is chosen. Everyday card-present
            # categories (groceries, fast food, transit) are visited far more often than
            # high-ticket or digital merchants, so weight frequency by card-present bias.
            "popularity": (rng.pareto(1.4, size=n_merchants) + 0.2)
            * (0.35 + 2.4 * np.array([MCC_CATALOG[j][4] for j in mcc_idx])),
        }
    )
    return Population(cards=cards, merchants=merchants)


def generate_legit(
    pop: Population,
    days: int = 30,
    start: str = "2026-07-01",
    seed: int = 11,
) -> pd.DataFrame:
    """Generate legitimate authorization traffic over `days`."""
    rng = np.random.default_rng(seed)
    cards, merch = pop.cards, pop.merchants
    start_ts = pd.Timestamp(start)

    # --- how many transactions per cardholder per day ---
    day_idx = np.arange(days)
    dow = (start_ts.dayofweek + day_idx) % 7
    day_mult = WEEKDAY_MULT[dow]                                    # (days,)
    lam = np.outer(cards["daily_rate"].to_numpy(), day_mult)        # (n_cards, days)
    counts = rng.poisson(lam)
    total = int(counts.sum())
    if total == 0:
        return pd.DataFrame(columns=list(TRANSACTION_FIELDS))

    card_ix = np.repeat(np.arange(len(cards)), counts.sum(axis=1))
    day_of = np.concatenate(
        [np.repeat(day_idx, counts[i]) for i in range(len(cards))]
    )

    # --- timestamps: diurnal hour + uniform minute/second ---
    hour = rng.choice(24, size=total, p=DIURNAL_P)
    ts = (
        start_ts
        + pd.to_timedelta(day_of, unit="D")
        + pd.to_timedelta(hour, unit="h")
        + pd.to_timedelta(rng.integers(0, 3600, size=total), unit="s")
    )

    # --- merchant choice: 70% from the cardholder's preferred MCCs, else popularity-weighted ---
    pop_w = merch["popularity"].to_numpy()
    pop_p = pop_w / pop_w.sum()
    m_ix = rng.choice(len(merch), size=total, p=pop_p)

    prefer_mask = rng.random(total) < 0.70
    merch_mcc = merch["mcc"].to_numpy()
    by_mcc: dict[str, np.ndarray] = {
        m: np.flatnonzero(merch_mcc == m) for m in set(merch_mcc)
    }
    pref_lists = cards["preferred_mccs"].to_numpy()
    for pos in np.flatnonzero(prefer_mask):
        pool_mccs = pref_lists[card_ix[pos]]
        cand = np.concatenate([by_mcc[m] for m in pool_mccs if m in by_mcc]) \
            if any(m in by_mcc for m in pool_mccs) else None
        if cand is not None and cand.size:
            m_ix[pos] = cand[rng.integers(0, cand.size)]

    # --- amount: lognormal around the merchant's typical ticket, scaled by affluence ---
    tick = merch["typical_ticket"].to_numpy()[m_ix]
    aff = cards["affluence"].to_numpy()[card_ix]
    amount = tick * aff * rng.lognormal(mean=-0.12, sigma=0.55, size=total)
    amount = np.round(np.clip(amount, 0.5, 25_000.0), 2)

    # --- channel / entry mode ---
    cp_bias = merch["cp_bias"].to_numpy()[m_ix]
    ecom_prop = cards["ecom_propensity"].to_numpy()[card_ix]
    # Card-present probability blends the merchant's nature and the cardholder's habits.
    p_cp = np.clip(cp_bias * (1.0 - 0.25 * ecom_prop), 0.0, 0.98)
    card_present = rng.random(total) < p_cp

    mcc_out = merch_mcc[m_ix]
    is_atm = mcc_out == "6011"
    channel = np.where(
        is_atm, Channel.ATM,
        np.where(card_present, Channel.POS, Channel.ECOM),
    ).astype(object)

    # Recurring subscriptions live in a few MCCs and are always card-not-present.
    recurring_mcc = np.isin(mcc_out, ["4899", "7372"])
    is_recurring = recurring_mcc & ~card_present & (rng.random(total) < 0.55)
    channel = np.where(is_recurring, Channel.RECURRING, channel)

    entry_mode = np.where(
        is_atm, EntryMode.CHIP,
        np.where(
            card_present,
            np.where(amount < 60, EntryMode.CONTACTLESS, EntryMode.CHIP),
            np.where(
                is_recurring, EntryMode.CREDENTIAL_ON_FILE,
                np.where(rng.random(total) < 0.62, EntryMode.NETWORK_TOKEN, EntryMode.ECOM_KEYED),
            ),
        ),
    ).astype(object)

    # --- geography ---
    issuer_country = cards["issuer_country"].to_numpy()[card_ix]
    m_country = merch["merchant_country"].to_numpy()[m_ix]
    travel = cards["travel_propensity"].to_numpy()[card_ix]
    # Domestic by default; card-present abroad only when the cardholder travels.
    keep_domestic = rng.random(total) > np.where(card_present, travel, travel + 0.06)
    merchant_country = np.where(keep_domestic, issuer_country, m_country)
    cross_border = merchant_country != issuer_country

    # --- verification results: legitimate traffic mostly verifies cleanly ---
    u = rng.random(total)
    avs = np.where(
        card_present, AvsResult.NOT_REQUESTED,
        np.where(u < 0.80, AvsResult.FULL_MATCH,
                 np.where(u < 0.90, AvsResult.ZIP_ONLY,
                          np.where(u < 0.95, AvsResult.ADDRESS_ONLY, AvsResult.UNAVAILABLE))),
    ).astype(object)

    u2 = rng.random(total)
    cvv = np.where(
        card_present, CvvResult.NOT_PROVIDED,
        np.where(is_recurring, CvvResult.NOT_PROCESSED,
                 np.where(u2 < 0.975, CvvResult.MATCH, CvvResult.NO_MATCH)),
    ).astype(object)

    # 3DS applies to e-commerce; recurring and card-present are out of scope.
    u3 = rng.random(total)
    three_ds = np.where(
        card_present | is_recurring | is_atm, ThreeDsStatus.NOT_APPLICABLE,
        np.where(u3 < 0.78, ThreeDsStatus.AUTHENTICATED,
                 np.where(u3 < 0.88, ThreeDsStatus.ATTEMPTED,
                          np.where(u3 < 0.96, ThreeDsStatus.CHALLENGE_REQUIRED,
                                   ThreeDsStatus.NOT_AUTHENTICATED))),
    ).astype(object)

    # PSD2 exemptions: low-value remote (<=EUR 30 equivalent), recurring, contactless, TRA.
    sca = np.where(
        is_recurring, ScaExemption.RECURRING,
        np.where(card_present & (amount < 60), ScaExemption.LOW_VALUE,
                 np.where((~card_present) & (amount <= 30), ScaExemption.LOW_VALUE,
                          np.where((~card_present) & (rng.random(total) < 0.18),
                                   ScaExemption.TRA, ScaExemption.NONE))),
    ).astype(object)

    # --- device / network: legitimate traffic overwhelmingly uses the primary device ---
    stable = rng.random(total) < 0.93
    prim_dev = cards["primary_device"].to_numpy()[card_ix]
    prim_ip = cards["primary_ip_prefix"].to_numpy()[card_ix]
    prim_ua = cards["ua_hash"].to_numpy()[card_ix]
    alt_dev = np.array([f"dev_alt_{rng.integers(0, 400_000):06d}" for _ in range(total)])
    alt_ip = np.array(
        [f"{rng.integers(11, 223)}.{rng.integers(0, 255)}.{rng.integers(0, 255)}.0/24"
         for _ in range(total)]
    )
    device_id = np.where(card_present, prim_dev, np.where(stable, prim_dev, alt_dev))
    ip_prefix = np.where(stable, prim_ip, alt_ip)
    ua_hash = np.where(stable, prim_ua, np.array([f"ua_{rng.integers(0, 9999):04d}" for _ in range(total)]))

    # --- authorization outcome ---
    u4 = rng.random(total)
    auth = np.where(u4 < 0.962, AuthResponse.APPROVED,
                    np.where(u4 < 0.988, AuthResponse.INSUFFICIENT_FUNDS,
                             AuthResponse.DO_NOT_HONOR)).astype(object)

    currency = cards["currency"].to_numpy()[card_ix]

    df = pd.DataFrame(
        {
            "transaction_id": [f"txn_{i:09d}" for i in range(total)],
            "timestamp": ts,
            "card_token": cards["card_token"].to_numpy()[card_ix],
            "account_id": cards["account_id"].to_numpy()[card_ix],
            "issuer_country": issuer_country,
            "amount": amount,
            "currency": currency,
            "amount_local": amount,
            "merchant_id": merch["merchant_id"].to_numpy()[m_ix],
            "merchant_name": merch["merchant_name"].to_numpy()[m_ix],
            "mcc": mcc_out,
            "merchant_country": merchant_country,
            "merchant_age_days": merch["merchant_age_days"].to_numpy()[m_ix],
            "channel": channel,
            "entry_mode": entry_mode,
            "card_present": card_present,
            "is_recurring": is_recurring,
            "device_id": device_id,
            "ip_prefix": ip_prefix,
            "user_agent_hash": ua_hash,
            "avs_result": avs,
            "cvv_result": cvv,
            "three_ds_status": three_ds,
            "sca_exemption": sca,
            "network_token_used": entry_mode == EntryMode.NETWORK_TOKEN,
            "cross_border": cross_border,
            "auth_response": auth,
            "is_fraud": 0,
            "attack_type": "",
            "scenario_id": "",
            "attack_strength": 0.0,
            "synthetic": True,
        }
    )
    return df.sort_values("timestamp", ignore_index=True)[list(TRANSACTION_FIELDS)]


def demo() -> None:
    """Self-check: fidelity properties we claim must actually hold."""
    pop = build_population(n_cardholders=300, n_merchants=80, seed=1)
    df = generate_legit(pop, days=14, seed=2)

    assert list(df.columns) == list(TRANSACTION_FIELDS), "column contract broken"
    assert len(df) > 500, f"implausibly little traffic: {len(df)}"
    assert df["is_fraud"].sum() == 0, "generator must emit no fraud"
    assert df["synthetic"].all(), "every row must be flagged synthetic"
    assert df["timestamp"].is_monotonic_increasing, "stream must be time-ordered"

    # Diurnal structure: night hours must be quieter than the evening peak.
    by_hour = df["timestamp"].dt.hour.value_counts()
    assert by_hour.get(3, 0) < by_hour.get(19, 1), "no diurnal rhythm present"

    # Habit stability: most card-not-present traffic uses the cardholder's primary device.
    cnp = df[~df["card_present"]]
    prim = dict(zip(pop.cards["card_token"], pop.cards["primary_device"]))
    share = (cnp["device_id"] == cnp["card_token"].map(prim)).mean()
    assert 0.80 < share < 0.99, f"device stability implausible: {share:.3f}"

    # Amounts must be right-skewed, as real ticket distributions are.
    assert df["amount"].median() < df["amount"].mean(), "amounts not right-skewed"

    # Card-present traffic should not carry 3-D Secure.
    assert (df.loc[df["card_present"], "three_ds_status"] == "X").all(), "3DS on card-present"

    # Channel mix must be payments-plausible: card-present dominates transaction *counts*.
    cnp_share = (~df["card_present"]).mean()
    assert 0.20 < cnp_share < 0.50, f"channel mix implausible: cnp={cnp_share:.1%}"

    print(
        f"OK  {len(df):,} txns · {pop.n_cards} cards · {pop.n_merchants} merchants · "
        f"median {df['amount'].median():.2f} · cnp {(~df['card_present']).mean():.1%} · "
        f"cross-border {df['cross_border'].mean():.1%}"
    )


if __name__ == "__main__":
    demo()
