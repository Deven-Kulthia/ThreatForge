"""FastAPI service for the Aegis command centre.

SAFETY BOUNDARY
---------------
This service has NO outbound network client. It imports no HTTP library, opens no sockets
to third parties, and holds no credentials. Every byte it serves is generated in-process by
`generator.py` and `attacks.py`. The attack simulator therefore cannot, by construction,
reach a live system — satisfying competition Rules §3(b) structurally rather than by policy.

The audit trail is a local SQLite file (Python stdlib), giving an append-only record of
every simulation and decision for reviewability.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .attacks import TAXONOMY, run_all, run_attack
from .detect import RULE_NAMES, Detector
from .explain import explain_one, global_importance
from .features import build_features
from .generator import build_population, generate_legit

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
AUDIT_DB = ARTIFACTS / "audit.db"

SAFETY_NOTICE = (
    "All data is SYNTHETIC. No real cardholder data, PII or production payment data is "
    "used. The attack simulator operates only on in-process synthetic data and has no "
    "network client; it cannot target any external system."
)


# --------------------------------------------------------------------------------------
# Audit trail
# --------------------------------------------------------------------------------------


def _audit_init() -> None:
    ARTIFACTS.mkdir(exist_ok=True)
    with closing(sqlite3.connect(AUDIT_DB)) as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, "
            "kind TEXT NOT NULL, actor TEXT NOT NULL, detail TEXT NOT NULL)"
        )
        c.commit()


def audit(kind: str, detail: dict[str, Any], actor: str = "system") -> None:
    with closing(sqlite3.connect(AUDIT_DB)) as c:
        c.execute(
            "INSERT INTO events (ts, kind, actor, detail) VALUES (?,?,?,?)",
            (pd.Timestamp.now("UTC").isoformat(), kind, actor, json.dumps(detail)[:4000]),
        )
        c.commit()


# --------------------------------------------------------------------------------------
# Engine — single in-process simulation environment
# --------------------------------------------------------------------------------------


class Engine:
    """Holds the synthetic environment, the trained detector and scored state."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.ready = False
        self.pop = None
        self.baseline = pd.DataFrame()      # legitimate traffic only
        self.stream = pd.DataFrame()        # everything currently in the environment
        self.scored = pd.DataFrame()
        self.detector: Detector | None = None
        self.campaigns: list[dict] = []
        self.train_seconds = 0.0

    def boot(self, n_cards: int = 700, n_merchants: int = 140, days: int = 30,
             seed: int = 42) -> dict:
        """Create the environment and train the defence on a first wave of attacks."""
        t = time.perf_counter()
        self.pop = build_population(n_cardholders=n_cards, n_merchants=n_merchants, seed=seed)
        self.baseline = generate_legit(self.pop, days=days, seed=seed + 1)

        # The defence is trained on simulated attacks — the closed loop's first turn.
        train_camps = run_all(self.pop, self.baseline, strength=0.6, seed=seed + 2)
        train_df = (
            pd.concat([self.baseline] + [c.transactions for c in train_camps],
                      ignore_index=True)
            .sort_values("timestamp", kind="stable").reset_index(drop=True)
        )
        self.detector = Detector().fit(train_df, train_df["is_fraud"].to_numpy())
        self.train_seconds = round(time.perf_counter() - t, 2)

        # The live environment starts as legitimate traffic only.
        self.stream = self.baseline.copy()
        self.scored = self.detector.score(self.stream)
        self.campaigns = []
        self.ready = True

        info = {"cards": int(n_cards), "merchants": int(n_merchants), "days": int(days),
                "baseline_transactions": int(len(self.baseline)),
                "training_transactions": int(len(train_df)),
                "training_attack_transactions": int(len(train_df) - len(self.baseline)),
                "train_seconds": self.train_seconds, "seed": seed}
        audit("environment_boot", info)
        return info

    def require(self) -> None:
        if not self.ready or self.detector is None:
            raise HTTPException(503, "environment not initialised — POST /api/environment/boot")

    def launch(self, attack_type: str, strength: float) -> dict:
        """Simulate one campaign, fold it into the live stream and score it."""
        self.require()
        if attack_type not in TAXONOMY:
            raise HTTPException(404, f"unknown attack_type: {attack_type}")
        camp = run_attack(attack_type, self.pop, self.baseline, strength=strength,
                          seed=int(time.time()) % 100_000,
                          t0=pd.Timestamp(self.stream["timestamp"].max()))
        self.stream = pd.concat([self.stream, camp.transactions], ignore_index=True) \
            .sort_values("timestamp", kind="stable").reset_index(drop=True)
        self.scored = self.detector.score(self.stream)

        ids = set(camp.transaction_ids)
        sub = self.scored[self.scored["transaction_id"].isin(ids)]
        caught = sub["risk_level"].isin(["HIGH", "CRITICAL"]).sum()
        md = camp.metadata()
        result = {
            **{k: v for k, v in md.items() if k != "synthetic_transaction_ids"},
            "detection": {
                "transactions": int(len(sub)),
                "flagged_high_or_critical": int(caught),
                "detection_rate": round(float(caught / max(len(sub), 1)), 4),
                "mean_risk": round(float(sub["risk_score"].mean()), 4),
                "max_risk": round(float(sub["risk_score"].max()), 4),
                "signals_fired": sorted({s for row in sub["detected_signals"] for s in row}),
            },
            "synthetic": True,
        }
        self.campaigns.append(result)
        audit("attack_simulated", {"attack_type": attack_type, "strength": strength,
                                   "n": int(len(sub)),
                                   "detection_rate": result["detection"]["detection_rate"]})
        return result


ENGINE = Engine()

# --------------------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------------------

app = FastAPI(
    title="Aegis — AI Defence Lab for Payment Security",
    description="Closed-loop adversarial AI for GenAI-era payment fraud. " + SAFETY_NOTICE,
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    # Local development origins only. No wildcard: this service is not intended to be
    # reachable from arbitrary origins even though it holds no sensitive data.
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:4173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    _audit_init()


class BootRequest(BaseModel):
    n_cards: int = Field(700, ge=50, le=5_000)
    n_merchants: int = Field(140, ge=10, le=1_000)
    days: int = Field(30, ge=3, le=120)
    seed: int = Field(42, ge=0, le=10_000_000)


class LaunchRequest(BaseModel):
    attack_type: str
    strength: float = Field(0.6, ge=0.0, le=1.0)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "ready": ENGINE.ready, "safety": SAFETY_NOTICE,
            "synthetic_only": True, "outbound_network": "none"}


@app.get("/api/taxonomy")
def taxonomy() -> dict:
    """The attack taxonomy — the 'Identify' pillar, served as structured data."""
    items = [{
        "id": s.id, "name": s.name, "category": s.category, "severity": s.severity,
        "genai_role": s.genai_role, "mitre_atlas": s.atlas, "channels": list(s.channels),
        "expected_signals": list(s.expected_signals),
        "hard_to_detect": s.hard_to_detect, "description": s.description,
    } for s in TAXONOMY.values()]
    return {"count": len(items),
            "categories": sorted({i["category"] for i in items}),
            "attacks": items}


@app.post("/api/environment/boot")
def boot(req: BootRequest) -> dict:
    with ENGINE.lock:
        return {"environment": ENGINE.boot(req.n_cards, req.n_merchants, req.days, req.seed),
                "safety": SAFETY_NOTICE}


@app.get("/api/environment")
def environment() -> dict:
    ENGINE.require()
    s = ENGINE.scored
    lv = s["risk_level"].value_counts().to_dict()
    return {
        "ready": True,
        "transactions": int(len(ENGINE.stream)),
        "baseline_transactions": int(len(ENGINE.baseline)),
        "attack_transactions": int(ENGINE.stream["is_fraud"].sum()),
        "campaigns_launched": len(ENGINE.campaigns),
        "risk_levels": {k: int(v) for k, v in lv.items()},
        "graph_stage_share": round(float(s["graph_evaluated"].mean()), 4),
        "train_seconds": ENGINE.train_seconds,
        "synthetic": True,
    }


@app.post("/api/attack/launch")
def launch(req: LaunchRequest) -> dict:
    with ENGINE.lock:
        return ENGINE.launch(req.attack_type, req.strength)


@app.get("/api/campaigns")
def campaigns() -> dict:
    ENGINE.require()
    return {"count": len(ENGINE.campaigns), "campaigns": ENGINE.campaigns}


@app.get("/api/transactions")
def transactions(limit: int = 100, offset: int = 0, min_risk: float = 0.0,
                 level: str | None = None, attack_type: str | None = None) -> dict:
    """Scored transactions, newest first. Ground truth is included — this is a lab."""
    ENGINE.require()
    limit = max(1, min(limit, 1_000))
    df = ENGINE.stream[["transaction_id", "timestamp", "card_token", "merchant_id",
                        "merchant_name", "mcc", "amount", "currency", "channel",
                        "entry_mode", "merchant_country", "cross_border",
                        "is_fraud", "attack_type"]]
    m = df.merge(ENGINE.scored, on="transaction_id", how="inner")
    m = m[m["risk_score"] >= min_risk]
    if level:
        m = m[m["risk_level"] == level.upper()]
    if attack_type:
        m = m[m["attack_type"] == attack_type]
    m = m.sort_values("timestamp", ascending=False)
    total = len(m)
    page = m.iloc[offset:offset + limit].copy()
    page["timestamp"] = page["timestamp"].astype(str)
    return {"total": int(total), "offset": offset, "limit": limit,
            "transactions": json.loads(page.to_json(orient="records")),
            "synthetic": True}


@app.get("/api/transactions/{txn_id}/explain")
def explain(txn_id: str) -> dict:
    ENGINE.require()
    pos = np.flatnonzero(ENGINE.stream["transaction_id"].to_numpy() == txn_id)
    if not len(pos):
        raise HTTPException(404, "unknown transaction_id")
    i = int(pos[0])
    row = ENGINE.stream.iloc[i]
    out = explain_one(ENGINE.detector, ENGINE.stream, ENGINE.scored, i)
    out["transaction"] = {
        "amount": float(row["amount"]), "currency": row["currency"],
        "merchant_name": row["merchant_name"], "mcc": row["mcc"],
        "channel": row["channel"], "entry_mode": row["entry_mode"],
        "timestamp": str(row["timestamp"]), "card_token": row["card_token"],
        "three_ds_status": row["three_ds_status"], "avs_result": row["avs_result"],
        "sca_exemption": row["sca_exemption"], "cross_border": bool(row["cross_border"]),
    }
    out["ground_truth"] = {"is_fraud": int(row["is_fraud"]),
                           "attack_type": row["attack_type"] or None}
    audit("explanation_viewed", {"transaction_id": txn_id,
                                 "risk_score": out["risk_score"]}, actor="analyst")
    return out


@app.get("/api/graph")
def graph(min_risk: float = 0.3, limit: int = 400, shared_only: bool = True) -> dict:
    """Entity graph for the riskiest traffic — cards, devices, networks, merchants.

    With `shared_only` (the default) the response is pruned to the subgraph induced by
    SHARED infrastructure: devices, network prefixes and merchants touching two or more
    distinct cards, plus the cards attached to them. That pruning is the whole point —
    an unpruned graph is mostly singleton card→merchant pairs, which renders as noise and
    hides the very structure that indicates a ring.
    """
    ENGINE.require()
    m = ENGINE.stream.merge(ENGINE.scored, on="transaction_id")
    m = m[m["risk_score"] >= min_risk].nlargest(min(limit, 1_000), "risk_score")

    # First pass: how many distinct cards touch each non-card entity?
    cards_per: dict[str, set[str]] = {}
    for _, r in m.iterrows():
        for key in (f"device:{r.device_id}", f"net:{r.ip_prefix}", f"merchant:{r.merchant_id}"):
            cards_per.setdefault(key, set()).add(r.card_token)

    keep = {k for k, v in cards_per.items() if len(v) >= 2} if shared_only else set(cards_per)

    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str, str], dict] = {}

    def node(nid: str, kind: str, label: str, risk: float) -> None:
        n = nodes.setdefault(nid, {"id": nid, "type": kind, "label": label,
                                   "risk": 0.0, "degree": 0})
        n["risk"] = max(n["risk"], round(float(risk), 3))
        n["degree"] += 1

    for _, r in m.iterrows():
        card = f"card:{r.card_token}"
        targets = [
            (f"device:{r.device_id}", "device", str(r.device_id), "uses_device"),
            (f"net:{r.ip_prefix}", "network", str(r.ip_prefix), "uses_network"),
            (f"merchant:{r.merchant_id}", "merchant", str(r.merchant_name), "pays"),
        ]
        linked = [t for t in targets if t[0] in keep]
        if not linked:
            continue                      # isolated card contributes no structure
        node(card, "card", str(r.card_token), r.risk_score)
        for nid, kind, label, rel in linked:
            node(nid, kind, label, r.risk_score)
            edges[(card, nid, rel)] = {"source": card, "target": nid, "kind": rel}

    return {"nodes": list(nodes.values()), "edges": list(edges.values()),
            "min_risk": min_risk, "shared_only": shared_only,
            "cards": sum(1 for n in nodes.values() if n["type"] == "card"),
            "synthetic": True}


@app.get("/api/metrics")
def metrics() -> dict:
    """Reproducible evaluation metrics, read from the artifact the harness writes."""
    p = ARTIFACTS / "metrics.json"
    if not p.exists():
        raise HTTPException(404, "no metrics yet — run: python -m backend.app.evaluate")
    return json.loads(p.read_text())


@app.get("/api/model/importance")
def importance(top: int = 15) -> dict:
    ENGINE.require()
    y = ENGINE.stream["is_fraud"].to_numpy()
    if y.sum() == 0:
        raise HTTPException(400, "no attack traffic yet — launch a campaign first")
    imp = global_importance(ENGINE.detector, ENGINE.stream, y, n_repeats=2)
    return {"scope": "global (permutation importance)",
            "caveat": "global only; per-row tree attribution is not claimed",
            "features": json.loads(imp.head(top).to_json(orient="records"))}


@app.get("/api/rules")
def rules() -> dict:
    return {"count": len(RULE_NAMES), "signals": RULE_NAMES}


@app.get("/api/audit")
def audit_trail(limit: int = 100) -> dict:
    with closing(sqlite3.connect(AUDIT_DB)) as c:
        rows = c.execute(
            "SELECT id, ts, kind, actor, detail FROM events ORDER BY id DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        ).fetchall()
    return {"count": len(rows),
            "events": [{"id": r[0], "ts": r[1], "kind": r[2], "actor": r[3],
                        "detail": json.loads(r[4])} for r in rows]}


@app.websocket("/ws/stream")
async def ws_stream(ws: WebSocket) -> None:
    """Replay the scored environment as a live authorization stream."""
    await ws.accept()
    try:
        if not ENGINE.ready:
            await ws.send_json({"type": "error",
                                "message": "environment not initialised"})
            await ws.close()
            return
        m = ENGINE.stream.merge(ENGINE.scored, on="transaction_id").sort_values("timestamp")
        cols = ["transaction_id", "timestamp", "card_token", "merchant_name", "mcc",
                "amount", "currency", "channel", "risk_score", "risk_level",
                "recommended_action", "is_fraud", "attack_type", "n_signals"]
        recs = json.loads(m[cols].tail(600).to_json(orient="records"))
        for r in recs:
            r["synthetic"] = True
            await ws.send_json({"type": "transaction", "data": r})
            await asyncio.sleep(0.08)
        await ws.send_json({"type": "complete", "sent": len(recs)})
    except WebSocketDisconnect:
        return
    except Exception as exc:                       # keep the socket contract clean
        await ws.send_json({"type": "error", "message": str(exc)[:200]})


def demo() -> None:
    """Self-check: boot, launch an attack, explain a decision, all in-process."""
    _audit_init()
    info = ENGINE.boot(n_cards=250, n_merchants=60, days=14, seed=7)
    assert info["baseline_transactions"] > 100
    res = ENGINE.launch("FAKE_STOREFRONT", 0.8)
    assert res["detection"]["transactions"] > 0
    assert res["mitre_atlas"] and res["expected_detection_signals"]
    env = environment()
    assert env["campaigns_launched"] == 1
    tx = transactions(limit=5, min_risk=0.0)
    assert tx["total"] > 0 and len(tx["transactions"]) == 5
    hi = ENGINE.scored.nlargest(1, "risk_score")["transaction_id"].iloc[0]
    ex = explain(hi)
    assert ex["reason_codes"] and ex["component_contributions"]
    g = graph(min_risk=0.3, limit=50)
    assert g["nodes"] and g["edges"]
    a = audit_trail(limit=5)
    assert a["count"] > 0
    print(f"OK  boot {info['train_seconds']}s · {env['transactions']:,} txns · "
          f"{res['attack_type']} detection {res['detection']['detection_rate']:.2f} · "
          f"graph {len(g['nodes'])} nodes · audit {a['count']} events")


if __name__ == "__main__":
    demo()
