"""Data-pipeline tests: generator, attack simulators, feature layer.

These complement the modules' own self-checks rather than repeating them. Each module's
`demo()` asserts its internal invariants; these tests cover reproducibility, edge cases
and cross-module contracts that a single module cannot check alone.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.app import attacks as A
from backend.app import features as F
from backend.app import generator as G
from backend.app.schema import GROUND_TRUTH_FIELDS, OBSERVABLE_FIELDS, TRANSACTION_FIELDS


@pytest.fixture(scope="module")
def pop():
    return G.build_population(n_cardholders=200, n_merchants=60, seed=1)


@pytest.fixture(scope="module")
def hist(pop):
    return G.generate_legit(pop, days=12, seed=2)


# --------------------------------------------------------------------------------------
# Reproducibility — every reported metric depends on this holding
# --------------------------------------------------------------------------------------


def test_population_is_deterministic():
    a = G.build_population(n_cardholders=80, n_merchants=25, seed=7)
    b = G.build_population(n_cardholders=80, n_merchants=25, seed=7)
    pd.testing.assert_frame_equal(a.cards.drop(columns=["preferred_mccs"]),
                                  b.cards.drop(columns=["preferred_mccs"]))
    pd.testing.assert_frame_equal(a.merchants, b.merchants)


def test_traffic_is_deterministic(pop):
    a = G.generate_legit(pop, days=6, seed=99)
    b = G.generate_legit(pop, days=6, seed=99)
    pd.testing.assert_frame_equal(a, b)


def test_different_seeds_differ(pop):
    a = G.generate_legit(pop, days=6, seed=1)
    b = G.generate_legit(pop, days=6, seed=2)
    assert len(a) != len(b) or not a["amount"].equals(b["amount"])


def test_campaign_is_deterministic(pop, hist):
    a = A.run_attack("FAKE_STOREFRONT", pop, hist, strength=0.6, seed=5)
    b = A.run_attack("FAKE_STOREFRONT", pop, hist, strength=0.6, seed=5)
    pd.testing.assert_frame_equal(a.transactions, b.transactions)


# --------------------------------------------------------------------------------------
# Schema contract
# --------------------------------------------------------------------------------------


def test_generator_emits_exact_schema(hist):
    assert list(hist.columns) == list(TRANSACTION_FIELDS)


def test_ground_truth_and_observable_fields_are_disjoint():
    assert not set(OBSERVABLE_FIELDS) & GROUND_TRUTH_FIELDS
    assert set(OBSERVABLE_FIELDS) | GROUND_TRUTH_FIELDS == set(TRANSACTION_FIELDS)


def test_amounts_and_timestamps_are_sane(hist):
    assert (hist["amount"] > 0).all()
    assert hist["amount"].max() < 100_000
    assert hist["timestamp"].is_monotonic_increasing
    assert hist["transaction_id"].is_unique


def test_generator_produces_no_fraud(hist):
    """Fraud must come only from the attack module, so the two code paths stay separable."""
    assert hist["is_fraud"].sum() == 0
    assert (hist["attack_type"] == "").all()


# --------------------------------------------------------------------------------------
# Attack taxonomy
# --------------------------------------------------------------------------------------


def test_every_taxonomy_entry_has_a_simulator():
    assert set(A.TAXONOMY) == set(A.SIMULATORS)


def test_taxonomy_metadata_is_complete():
    for spec in A.TAXONOMY.values():
        assert spec.name and spec.category and spec.description
        assert spec.genai_role, f"{spec.id} does not state what GenAI changed"
        assert spec.atlas, f"{spec.id} is unmapped to MITRE ATLAS"
        assert spec.expected_signals, f"{spec.id} declares no expected signals"
        assert 1 <= spec.severity <= 5
        assert spec.channels


@pytest.mark.parametrize("attack_id", sorted(A.TAXONOMY))
def test_each_attack_simulates_and_labels(attack_id, pop, hist):
    c = A.run_attack(attack_id, pop, hist, strength=0.7, seed=11)
    assert len(c.transactions) > 0
    assert (c.transactions["is_fraud"] == 1).all()
    assert c.transactions["synthetic"].all()
    assert (c.transactions["attack_type"] == attack_id).all()
    assert list(c.transactions.columns) == list(TRANSACTION_FIELDS)
    md = c.metadata()
    assert md["ground_truth"] == "fraud"
    assert md["n_transactions"] == len(c.transactions)
    assert md["scenario_id"].startswith("SCN-")


def test_transaction_ids_are_globally_unique(pop, hist):
    """Collisions here silently corrupt every join between stream and scores."""
    camps = A.run_all(pop, hist, strength=0.6, seed=3)
    ids = [t for c in camps for t in c.transaction_ids]
    assert len(ids) == len(set(ids))
    assert not set(ids) & set(hist["transaction_id"])


def test_repeated_campaigns_of_same_type_do_not_collide(pop, hist):
    a = A.run_attack("MULE_FANOUT", pop, hist, strength=0.6, seed=1)
    b = A.run_attack("MULE_FANOUT", pop, hist, strength=0.6, seed=2)
    assert not set(a.transaction_ids) & set(b.transaction_ids)


def test_strength_scales_campaign_size(pop, hist):
    small = A.run_attack("CARD_TESTING_MICRO", pop, hist, strength=0.1, seed=4)
    big = A.run_attack("CARD_TESTING_MICRO", pop, hist, strength=1.0, seed=4)
    assert len(big.transactions) > len(small.transactions)


def test_campaigns_spread_across_the_window(pop, hist):
    """Without spread, a temporal split has no positives to train on."""
    camps = A.run_all(pop, hist, strength=0.6, seed=8)
    starts = pd.Series([c.transactions["timestamp"].min() for c in camps])
    lo, hi = hist["timestamp"].min(), hist["timestamp"].max()
    frac = (starts - lo) / (hi - lo)
    assert frac.min() < 0.35 and frac.max() > 0.65


def test_hard_attacks_are_marked_and_present():
    hard = [s for s in A.TAXONOMY.values() if s.hard_to_detect]
    assert len(hard) >= 8, "taxonomy should include genuinely difficult cases"


def test_mastercard_named_threats_are_covered():
    """The announcement names four priority threats; all four must be represented."""
    cats = {s.category for s in A.TAXONOMY.values()}
    assert "Synthetic identity" in cats
    assert "Deepfake / KYC" in cats
    assert "Merchant fraud" in cats
    assert "Scam / social engineering" in cats


# --------------------------------------------------------------------------------------
# Feature layer
# --------------------------------------------------------------------------------------


def test_features_are_finite_and_complete(hist):
    X = F.build_features(hist)
    assert len(X) == len(hist)
    assert X.notna().all().all()
    assert np.isfinite(X.to_numpy()).all()


def test_features_exclude_ground_truth(hist):
    """Label leakage must be structurally impossible, not merely discouraged."""
    X = F.build_features(hist)
    assert not set(X.columns) & GROUND_TRUTH_FIELDS
    for banned in ("is_fraud", "attack_type", "attack_strength", "scenario_id"):
        assert not any(banned in c for c in X.columns)


def test_features_are_causal(pop, hist):
    """Recomputing on a time prefix must reproduce that prefix exactly."""
    camp = A.run_attack("ATO_CREDENTIAL_STUFF", pop, hist, strength=0.8, seed=3)
    df = (pd.concat([hist, camp.transactions], ignore_index=True)
          .sort_values("timestamp", kind="stable").reset_index(drop=True))
    full = F.build_features(df)
    cut = int(len(df) * 0.5)
    prefix = F.build_features(df.iloc[:cut])
    pd.testing.assert_frame_equal(full.iloc[:cut].reset_index(drop=True),
                                  prefix.reset_index(drop=True), atol=1e-9)


def test_first_event_per_card_has_no_history(hist):
    X = F.build_features(hist)
    d = hist.sort_values("timestamp", kind="stable").reset_index(drop=True)
    first = (~d.duplicated("card_token", keep="first")).to_numpy()
    assert (X.loc[first, "card_txn_24h"] == 0).all()
    assert (X.loc[first, "card_history_len"] == 0).all()
    assert (X.loc[first, "card_secs_since_prev"] == -1).all()


def test_features_handle_single_row(hist):
    X = F.build_features(hist.iloc[:1])
    assert len(X) == 1
    assert np.isfinite(X.to_numpy()).all()


def test_features_handle_empty_frame():
    empty = pd.DataFrame(columns=list(TRANSACTION_FIELDS))
    empty["timestamp"] = pd.to_datetime(empty["timestamp"])
    empty["amount"] = empty["amount"].astype(float)
    X = F.build_features(empty)
    assert len(X) == 0


def test_shared_device_attack_lights_up_fan_in(pop, hist):
    """A behavioural claim, not just a smoke test: the feature must separate the attack."""
    camp = A.run_attack("ATO_CREDENTIAL_STUFF", pop, hist, strength=0.9, seed=6)
    df = (pd.concat([hist, camp.transactions], ignore_index=True)
          .sort_values("timestamp", kind="stable").reset_index(drop=True))
    X = F.build_features(df)
    atk = df["is_fraud"].to_numpy() == 1
    assert X.loc[atk, "dev_prior_cards"].max() > X.loc[~atk, "dev_prior_cards"].max()
