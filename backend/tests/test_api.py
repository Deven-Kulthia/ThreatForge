"""API contract tests, driven in-process through FastAPI's TestClient.

A small environment is booted once for the module: the point is to verify contracts and
error handling, not to re-measure detection quality.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import api as APIMOD
from backend.app.attacks import TAXONOMY


@pytest.fixture(scope="module")
def client():
    APIMOD._audit_init()
    with TestClient(APIMOD.app) as c:
        yield c


@pytest.fixture(scope="module")
def booted(client):
    r = client.post("/api/environment/boot",
                    json={"n_cards": 180, "n_merchants": 50, "days": 10, "seed": 3})
    assert r.status_code == 200
    return client


# --------------------------------------------------------------------------------------
# Contracts available before boot
# --------------------------------------------------------------------------------------


def test_health_always_answers(client):
    """Health must never 503 — the UI polls it to decide whether to show the boot screen."""
    r = client.get("/api/health")
    assert r.status_code == 200
    b = r.json()
    assert b["status"] == "ok"
    assert b["synthetic_only"] is True
    assert b["outbound_network"] == "none"
    assert "SYNTHETIC" in b["safety"]


def test_taxonomy_is_served_without_an_environment(client):
    r = client.get("/api/taxonomy")
    assert r.status_code == 200
    b = r.json()
    assert b["count"] == len(TAXONOMY)
    assert len(b["attacks"]) == len(TAXONOMY)
    for a in b["attacks"]:
        assert a["mitre_atlas"] and a["expected_signals"] and a["genai_role"]


def test_rules_endpoint_lists_signals(client):
    b = client.get("/api/rules").json()
    assert b["count"] > 20
    assert len(b["signals"]) == b["count"]


# --------------------------------------------------------------------------------------
# Boot and environment
# --------------------------------------------------------------------------------------


def test_boot_reports_a_trained_environment(booted):
    b = booted.get("/api/environment").json()
    assert b["ready"] is True
    assert b["transactions"] > 100
    assert b["synthetic"] is True
    assert sum(b["risk_levels"].values()) == b["transactions"]


def test_boot_rejects_out_of_range_input(client):
    assert client.post("/api/environment/boot", json={"n_cards": 1}).status_code == 422
    assert client.post("/api/environment/boot", json={"days": 9999}).status_code == 422


# --------------------------------------------------------------------------------------
# Attack simulation
# --------------------------------------------------------------------------------------


def test_launch_returns_ground_truth_and_detection(booted):
    r = booted.post("/api/attack/launch",
                    json={"attack_type": "FAKE_STOREFRONT", "strength": 0.8})
    assert r.status_code == 200
    b = r.json()
    assert b["attack_type"] == "FAKE_STOREFRONT"
    assert b["ground_truth"] == "fraud"
    assert b["mitre_atlas"]
    assert b["expected_detection_signals"]
    assert b["detection"]["transactions"] > 0
    assert 0.0 <= b["detection"]["detection_rate"] <= 1.0
    # The response must not leak the full id list into every client payload.
    assert "synthetic_transaction_ids" not in b


def test_launch_rejects_unknown_attack(booted):
    r = booted.post("/api/attack/launch", json={"attack_type": "NOT_A_REAL_ATTACK"})
    assert r.status_code == 404


def test_launch_validates_strength_bounds(booted):
    assert booted.post("/api/attack/launch",
                       json={"attack_type": "MULE_FANOUT", "strength": 5}).status_code == 422
    assert booted.post("/api/attack/launch",
                       json={"attack_type": "MULE_FANOUT", "strength": -1}).status_code == 422


def test_campaigns_accumulate(booted):
    before = booted.get("/api/campaigns").json()["count"]
    booted.post("/api/attack/launch", json={"attack_type": "MULE_FANOUT", "strength": 0.5})
    after = booted.get("/api/campaigns").json()["count"]
    assert after == before + 1


# --------------------------------------------------------------------------------------
# Transactions, explanation, graph
# --------------------------------------------------------------------------------------


def test_transactions_paginate_and_filter(booted):
    b = booted.get("/api/transactions?limit=10").json()
    assert len(b["transactions"]) == 10
    assert b["total"] >= 10

    hi = booted.get("/api/transactions?limit=50&min_risk=0.6").json()
    assert all(t["risk_score"] >= 0.6 for t in hi["transactions"])

    lvl = booted.get("/api/transactions?limit=25&level=CRITICAL").json()
    assert all(t["risk_level"] == "CRITICAL" for t in lvl["transactions"])


def test_transaction_limit_is_capped(booted):
    b = booted.get("/api/transactions?limit=99999").json()
    assert len(b["transactions"]) <= 1000


def test_explain_returns_exact_decomposition(booted):
    top = booted.get("/api/transactions?limit=1&min_risk=0.5").json()["transactions"]
    assert top, "expected at least one elevated-risk transaction"
    tid = top[0]["transaction_id"]
    b = booted.get(f"/api/transactions/{tid}/explain").json()
    assert b["transaction_id"] == tid
    assert b["reason_codes"]
    assert b["component_contributions"]
    assert b["counterfactual"]
    assert "not claimed" in b["caveat"].lower()
    assert b["transaction"]["amount"] > 0
    assert b["ground_truth"]["is_fraud"] in (0, 1)


def test_explain_unknown_transaction_is_404(booted):
    assert booted.get("/api/transactions/does_not_exist/explain").status_code == 404


def test_graph_is_pruned_to_shared_infrastructure(booted):
    b = booted.get("/api/graph?min_risk=0.3&limit=200").json()
    assert b["shared_only"] is True
    ids = {n["id"] for n in b["nodes"]}
    # Every edge must reference nodes that are actually present.
    for e in b["edges"]:
        assert e["source"] in ids and e["target"] in ids
    # No orphan nodes: pruning exists precisely to remove them.
    linked = {e["source"] for e in b["edges"]} | {e["target"] for e in b["edges"]}
    assert ids == linked


# --------------------------------------------------------------------------------------
# Audit trail
# --------------------------------------------------------------------------------------


def test_audit_records_boot_and_attacks(booted):
    b = booted.get("/api/audit?limit=100").json()
    kinds = {e["kind"] for e in b["events"]}
    assert "environment_boot" in kinds
    assert "attack_simulated" in kinds
    # Newest first, so ids descend.
    ids = [e["id"] for e in b["events"]]
    assert ids == sorted(ids, reverse=True)


def test_audit_limit_is_capped(booted):
    b = booted.get("/api/audit?limit=99999").json()
    assert len(b["events"]) <= 500


# --------------------------------------------------------------------------------------
# Error handling before the environment exists
# --------------------------------------------------------------------------------------


def test_environment_dependent_routes_503_before_boot():
    """A fresh engine must fail clearly rather than returning misleading empty data."""
    fresh = APIMOD.Engine()
    original = APIMOD.ENGINE
    APIMOD.ENGINE = fresh
    try:
        with TestClient(APIMOD.app) as c:
            assert c.get("/api/environment").status_code == 503
            assert c.get("/api/transactions").status_code == 503
            assert c.get("/api/graph").status_code == 503
    finally:
        APIMOD.ENGINE = original
