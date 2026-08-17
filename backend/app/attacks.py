"""GenAI-era payment fraud attack taxonomy and safe synthetic simulator.

SAFETY BOUNDARY (competition Rules §3b)
---------------------------------------
Everything in this module operates on in-memory synthetic DataFrames produced by
`generator.py`. There is no network client, no credential handling, and no external
target of any kind. Nothing here can reach a live system, and nothing here constitutes
operational instructions for committing fraud: attacks are modelled at the level of
*observable behavioural change in a transaction stream*, which is what a defender needs
in order to build detection, and nothing lower.

DESIGN PRINCIPLE — feasible-action attacks
------------------------------------------
The adversarial-ML literature's standing criticism of tabular attack research is that it
perturbs features an attacker cannot actually control (you cannot set `amount = 43.7291`,
and you certainly cannot forge an EMV application transaction counter). Every attack here
is therefore restricted to the *attacker's real action space*:

    CONTROLLABLE  amount, timing, cadence, merchant selection, MCC selection, channel,
                  device, IP, user agent, which card is used, sequencing across cards
    NOT TOUCHED   issuer-side verification results that the attacker cannot forge,
                  cryptogram validity, counters, network token assurance

Attacks that manipulate verification fields do so only where the real-world attack path
genuinely produces that outcome (e.g. an intercepted OTP legitimately yields a 3-D Secure
"authenticated" status — that is exactly why OTP interception is dangerous).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .schema import (
    COUNTRIES,
    CURRENCY_BY_COUNTRY,
    HIGH_RISK_MCCS,
    TRANSACTION_FIELDS,
    AuthResponse,
    AvsResult,
    Channel,
    CvvResult,
    EntryMode,
    ScaExemption,
    ThreeDsStatus,
)

# --------------------------------------------------------------------------------------
# Taxonomy
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AttackSpec:
    """Metadata for one attack vector.

    `expected_signals` is the ground truth for *detectability*: the signals a competent
    detector ought to fire on. It lets us measure per-signal recall, not just overall
    accuracy — i.e. whether the defense caught an attack *for the right reason*.
    """

    id: str
    name: str
    category: str
    genai_role: str          # what generative AI specifically changes about this attack
    atlas: str               # MITRE ATLAS / ATT&CK alignment for the ML-relevant step
    channels: tuple[str, ...]
    expected_signals: tuple[str, ...]
    severity: int            # 1 (nuisance) .. 5 (systemic)
    description: str
    hard_to_detect: bool = False   # deliberately overlaps legitimate behaviour


TAXONOMY: dict[str, AttackSpec] = {}


def _spec(**kw) -> None:
    s = AttackSpec(**kw)
    TAXONOMY[s.id] = s


# --- A. Synthetic identity (Mastercard-named priority threat) -------------------------
_spec(
    id="SYNTH_ID_BUILDUP",
    name="Synthetic identity history building",
    category="Synthetic identity",
    genai_role="LLMs mass-produce coherent applicant personas and plausible life-event "
    "narratives, so an identity survives manual review that would previously have caught it.",
    atlas="ATLAS TA0002 Resource Development (persona fabrication)",
    channels=("ECOM", "POS"),
    expected_signals=("new_account_velocity", "thin_history", "device_sharing"),
    severity=4,
    description="Freshly minted synthetic accounts transact small and clean to accrue a "
    "credible history before monetisation. Individually unremarkable by design.",
    hard_to_detect=True,
)
_spec(
    id="SYNTH_ID_BUSTOUT",
    name="Synthetic identity bust-out",
    category="Synthetic identity",
    genai_role="Generative tooling scales the number of aged identities available to burn "
    "simultaneously, turning bust-out from artisanal to industrial.",
    atlas="ATLAS AML.T0048 External Harms / Financial Harm",
    channels=("ECOM", "POS"),
    expected_signals=("amount_spike_vs_baseline", "high_risk_mcc", "velocity_burst",
                      "credit_limit_exhaustion"),
    severity=5,
    description="After the build-up phase, the identity spends to exhaustion in a short "
    "window across high-liquidity categories, then goes dark.",
)
_spec(
    id="GENAI_DOC_FARM",
    name="Generated-document application farm",
    category="Synthetic identity",
    genai_role="Image models produce unlimited passable identity documents and selfies; "
    "the bottleneck moves from document production to infrastructure reuse.",
    atlas="ATLAS TA0002 Resource Development",
    channels=("ECOM",),
    expected_signals=("device_sharing", "ip_concentration", "ua_homogeneity",
                      "new_account_velocity"),
    severity=4,
    description="A large batch of accounts onboarded from one operational footprint. The "
    "documents are unique but the infrastructure is not.",
)

# --- B. Deepfake KYC and account takeover (Mastercard-named) --------------------------
_spec(
    id="DEEPFAKE_KYC_ONBOARD",
    name="Deepfake KYC onboarding bypass",
    category="Deepfake / KYC",
    genai_role="Real-time face swap and injection attacks defeat liveness checks that "
    "assume a camera observes a physical person.",
    atlas="ATLAS AML.T0015 Evade AI Model (liveness/biometric model)",
    channels=("ECOM",),
    expected_signals=("new_account_velocity", "immediate_high_value", "high_risk_mcc",
                      "geo_mismatch"),
    severity=5,
    description="An account passes biometric onboarding via synthetic media, then monetises "
    "immediately — no history-building patience at all.",
)
_spec(
    id="VOICE_CLONE_ATO",
    name="Voice-clone call-centre takeover",
    category="Account takeover",
    genai_role="Seconds of sampled audio clone a cardholder's voice well enough to pass "
    "human and voice-biometric verification in a service call.",
    atlas="ATLAS AML.T0015 Evade AI Model (voice biometric)",
    channels=("ECOM", "MOTO"),
    expected_signals=("device_change", "geo_mismatch", "profile_change_then_spend",
                      "behavioral_drift"),
    severity=5,
    description="Support-channel takeover: contact details are changed, then spend follows "
    "from unfamiliar infrastructure while the account itself looks legitimate.",
)
_spec(
    id="ATO_CREDENTIAL_STUFF",
    name="Automated credential stuffing to takeover",
    category="Account takeover",
    genai_role="Agentic browser automation solves challenges and adapts to varied login "
    "flows without bespoke scripting per target.",
    atlas="ATT&CK T1110.004 Credential Stuffing",
    channels=("ECOM",),
    expected_signals=("device_sharing", "ip_concentration", "many_cards_one_device",
                      "machine_cadence"),
    severity=4,
    description="One operational footprint touches many unrelated accounts in a short "
    "window; successful sessions convert to spend.",
)
_spec(
    id="SIM_SWAP_OTP",
    name="SIM-swap / OTP interception",
    category="Account takeover",
    genai_role="Generated pretext scripts and cloned voices make carrier-side social "
    "engineering repeatable at scale.",
    atlas="ATT&CK T1451 SIM Card Swap",
    channels=("ECOM",),
    expected_signals=("device_change", "geo_mismatch", "authenticated_but_anomalous",
                      "behavioral_drift"),
    severity=5,
    description="The strong-authentication step genuinely succeeds because the attacker "
    "controls the second factor. Verification fields look clean; behaviour does not.",
    hard_to_detect=True,
)

# --- C. Fake merchants and laundering (Mastercard-named) ------------------------------
_spec(
    id="FAKE_STOREFRONT",
    name="Fabricated merchant storefront",
    category="Merchant fraud",
    genai_role="Generative tooling produces a complete, convincing storefront — copy, "
    "product imagery, reviews, policies — in minutes rather than weeks.",
    atlas="ATLAS TA0002 Resource Development",
    channels=("ECOM",),
    expected_signals=("new_merchant_risk", "merchant_ticket_anomaly", "avs_failure",
                      "high_risk_mcc"),
    severity=4,
    description="A newly registered merchant takes card-not-present volume at ticket sizes "
    "inconsistent with its declared category, then disappears before chargebacks land.",
)
_spec(
    id="TRANSACTION_LAUNDERING",
    name="Transaction laundering / MCC misrepresentation",
    category="Merchant fraud",
    genai_role="Automated content generation sustains many plausible front-shop facades "
    "concurrently, each masking the same underlying prohibited activity.",
    atlas="ATLAS AML.T0048 External Harms",
    channels=("ECOM",),
    expected_signals=("mcc_inconsistency", "merchant_ticket_anomaly", "cross_border",
                      "beneficiary_concentration"),
    severity=4,
    description="Volume for a prohibited or high-risk category is presented under a benign "
    "MCC, so category-based controls never engage.",
    hard_to_detect=True,
)
_spec(
    id="REFUND_ABUSE_COLLUSION",
    name="Collusive refund and credit abuse",
    category="Merchant fraud",
    genai_role="LLM-drafted dispute narratives industrialise claim submission and tune "
    "wording against known adjudication criteria.",
    atlas="ATLAS AML.T0048 External Harms",
    channels=("ECOM",),
    expected_signals=("refund_ratio_anomaly", "beneficiary_concentration", "device_sharing"),
    severity=3,
    description="Purchases are followed by disproportionate credits to a small beneficiary "
    "set, extracting value through the refund rail rather than the purchase rail.",
)

# --- D. AI-enabled scams (Mastercard-named) ------------------------------------------
_spec(
    id="APP_SCAM_LLM",
    name="LLM-driven authorised push payment scam",
    category="Scam / social engineering",
    genai_role="Conversational models sustain thousands of individually tailored, "
    "emotionally coherent grooming conversations at once.",
    atlas="ATT&CK T1566 Phishing (payment-directed variant)",
    channels=("ECOM",),
    expected_signals=("first_time_beneficiary", "amount_spike_vs_baseline",
                      "session_duress_pattern", "authenticated_but_anomalous"),
    severity=5,
    description="The genuine cardholder, on their genuine device, willingly authorises the "
    "payment. Every credential signal is clean — only intent is wrong.",
    hard_to_detect=True,
)
_spec(
    id="ROMANCE_PIG_BUTCHERING",
    name="Escalating investment / romance scam",
    category="Scam / social engineering",
    genai_role="Persistent AI personas maintain long-horizon relationships and adapt "
    "escalation pacing to each victim's resistance.",
    atlas="ATT&CK T1566 Phishing",
    channels=("ECOM",),
    expected_signals=("escalating_amount_sequence", "beneficiary_concentration",
                      "first_time_beneficiary", "behavioral_drift"),
    severity=5,
    description="A slow escalation of victim-authorised transfers toward one beneficiary "
    "cluster over days or weeks. Each single payment looks defensible.",
    hard_to_detect=True,
)
_spec(
    id="INVOICE_REDIRECT_BEC",
    name="Invoice redirection / business email compromise",
    category="Scam / social engineering",
    genai_role="Models mimic a specific counterparty's writing style and thread history, "
    "removing the linguistic tells staff are trained to spot.",
    atlas="ATT&CK T1566.002 Spearphishing Link",
    channels=("ECOM", "MOTO"),
    expected_signals=("first_time_beneficiary", "amount_spike_vs_baseline",
                      "corporate_exemption_abuse", "beneficiary_concentration"),
    severity=4,
    description="A high-value payment to a newly substituted beneficiary, structurally "
    "identical to a routine supplier settlement.",
    hard_to_detect=True,
)

# --- E. Card testing and enumeration -------------------------------------------------
_spec(
    id="CARD_TESTING_MICRO",
    name="Micro-amount card testing",
    category="Enumeration",
    genai_role="Agentic automation distributes probing across merchants and time to stay "
    "under per-merchant thresholds without human coordination.",
    atlas="ATT&CK T1110 Brute Force",
    channels=("ECOM",),
    expected_signals=("micro_amount_cluster", "many_cards_one_merchant", "machine_cadence",
                      "auth_failure_ratio"),
    severity=3,
    description="Many candidate credentials validated with negligible-value authorisations "
    "before the viable ones are sold or used.",
)
_spec(
    id="BIN_ENUMERATION_BURST",
    name="BIN range enumeration burst",
    category="Enumeration",
    genai_role="Automated agents parallelise generation-and-test across BIN ranges and "
    "rotate infrastructure between bursts.",
    atlas="ATT&CK T1110 Brute Force",
    channels=("ECOM",),
    expected_signals=("bin_sequence_pattern", "auth_failure_ratio", "machine_cadence",
                      "ip_concentration"),
    severity=3,
    description="Sequentially related credentials probed in a tight burst, producing a "
    "distinctive decline signature.",
)

# --- F. Rings and mule networks ------------------------------------------------------
_spec(
    id="MULE_FANOUT",
    name="Mule account fan-out",
    category="Fraud ring",
    genai_role="Automated recruitment messaging scales mule acquisition, so the network "
    "layer grows faster than manual investigation can map it.",
    atlas="ATLAS AML.T0048 External Harms",
    channels=("ECOM",),
    expected_signals=("beneficiary_concentration", "graph_fanin", "ring_component",
                      "rapid_pass_through"),
    severity=5,
    description="Value from many compromised sources converges on a small beneficiary set. "
    "Invisible per-transaction; obvious as a graph.",
)
_spec(
    id="COORDINATED_RING",
    name="Coordinated multi-card ring",
    category="Fraud ring",
    genai_role="Coordination tooling lets a small crew operate many identities with "
    "consistent tradecraft and shared infrastructure.",
    atlas="ATT&CK T1078 Valid Accounts",
    channels=("ECOM", "POS"),
    expected_signals=("device_sharing", "ip_concentration", "ring_component",
                      "graph_fanin", "synchronised_timing"),
    severity=5,
    description="Distinct cards linked by shared devices and network infrastructure, "
    "transacting in loose synchrony.",
)

# --- G. Agentic commerce (the genuinely new surface) ---------------------------------
_spec(
    id="AGENT_IMPERSONATION",
    name="Autonomous shopping-agent impersonation",
    category="Agentic commerce",
    genai_role="As delegated AI agents legitimately transact on cardholders' behalf, "
    "attacker traffic can hide inside a brand-new and poorly-baselined traffic class.",
    atlas="ATLAS AML.T0015 Evade AI Model",
    channels=("ECOM",),
    expected_signals=("machine_cadence", "ua_homogeneity", "no_human_session_rhythm",
                      "device_sharing"),
    severity=4,
    description="Fraudulent volume presented as legitimate delegated-agent commerce, at "
    "machine cadence and without human interaction rhythm.",
)
_spec(
    id="AGENT_PROMPT_INJECTION",
    name="Prompt injection via merchant-controlled fields",
    category="Agentic commerce",
    genai_role="Merchant-supplied free text reaches LLM-based risk narration and agent "
    "reasoning, making the data plane an instruction channel.",
    atlas="ATLAS AML.T0051 LLM Prompt Injection",
    channels=("ECOM",),
    expected_signals=("injection_pattern_in_text", "new_merchant_risk",
                      "merchant_ticket_anomaly"),
    severity=4,
    description="Adversarial instructions embedded in merchant descriptors, aimed at any "
    "downstream model that reads transaction text.",
)

# --- H. Adaptive evasion (the closed-loop adversary) ---------------------------------
_spec(
    id="VELOCITY_EVASION",
    name="Velocity-threshold evasion",
    category="Adaptive evasion",
    genai_role="An adaptive agent infers effective thresholds from decline feedback and "
    "re-plans spacing automatically.",
    atlas="ATLAS AML.T0015 Evade AI Model",
    channels=("ECOM", "POS"),
    expected_signals=("behavioral_drift", "sub_threshold_pacing", "device_change"),
    severity=4,
    description="The same total extraction, deliberately paced to stay under count and "
    "value velocity limits.",
    hard_to_detect=True,
)
_spec(
    id="SCA_EXEMPTION_ABUSE",
    name="Low-value SCA exemption stacking",
    category="Adaptive evasion",
    genai_role="Automated planning keeps every authorisation inside an exemption envelope "
    "across merchants and time without manual bookkeeping.",
    atlas="ATLAS AML.T0015 Evade AI Model",
    channels=("ECOM",),
    expected_signals=("sub_threshold_pacing", "low_value_exemption_cluster",
                      "beneficiary_concentration", "no_3ds_challenge"),
    severity=4,
    description="Extraction structured entirely beneath the low-value remote-payment "
    "exemption ceiling so that strong authentication is never triggered.",
    hard_to_detect=True,
)
_spec(
    id="TRA_THRESHOLD_GAMING",
    name="Risk-analysis threshold gaming",
    category="Adaptive evasion",
    genai_role="Query-efficient probing maps a scoring boundary from accept/decline "
    "feedback alone, with no model access.",
    atlas="ATLAS AML.T0043 Craft Adversarial Data",
    channels=("ECOM",),
    expected_signals=("sub_threshold_pacing", "amount_just_below_band",
                      "exemption_claim_anomaly"),
    severity=4,
    description="Amounts placed just inside the most permissive risk band, exploiting "
    "banded exemption logic rather than attacking the model directly.",
    hard_to_detect=True,
)
_spec(
    id="ADAPTIVE_MIMICRY",
    name="Victim-profile mimicry",
    category="Adaptive evasion",
    genai_role="A model fitted to the victim's own transaction history generates fraud "
    "drawn from the victim's legitimate behavioural distribution.",
    atlas="ATLAS AML.T0043 Craft Adversarial Data",
    channels=("ECOM", "POS"),
    expected_signals=("beneficiary_concentration", "subtle_drift", "graph_fanin"),
    severity=5,
    description="The hardest case in this taxonomy: fraud that matches the victim's usual "
    "merchants, amounts, timing and device. Designed to be statistically near-invisible, "
    "so that residual detection must come from network structure rather than per-transaction "
    "anomaly.",
    hard_to_detect=True,
)

_spec(
    id="MANDATE_REPLAY_ABUSE",
    name="Agent mandate replay / scope substitution",
    category="Agentic commerce",
    genai_role="Delegated-payment mandates are a brand-new artefact class; where signature "
    "scope or freshness is not fully enforced, a captured authorisation intent can be reused "
    "or re-pointed.",
    atlas="ATT&CK T1550 Use Alternate Authentication Material",
    channels=("ECOM",),
    expected_signals=("mandate_mismatch", "amount_just_below_band", "machine_cadence",
                      "beneficiary_concentration"),
    severity=5,
    description="An authorisation whose merchant, amount or currency diverges from the "
    "cardholder's signed payment instruction — the failure mode that AP2 mandate signing and "
    "network-level instruction matching are explicitly designed to prevent.",
    hard_to_detect=True,
)
_spec(
    id="FIRST_PARTY_DISPUTE",
    name="First-party dispute abuse",
    category="First-party fraud",
    genai_role="Fluent, consistent dispute narratives are volume-produced, eroding the "
    "'story quality' signal reviewers relied on.",
    atlas="ATLAS AML.T0048 External Harms",
    channels=("ECOM",),
    expected_signals=("refund_ratio_anomaly", "post_delivery_dispute",
                      "repeat_claimant_pattern"),
    severity=3,
    description="The genuine cardholder transacts genuinely, then disputes after receiving "
    "value. Concentration appears per customer rather than per merchant.",
    hard_to_detect=True,
)


# --------------------------------------------------------------------------------------
# Campaign result
# --------------------------------------------------------------------------------------


@dataclass
class Campaign:
    """The output of one simulated attack, with full ground truth attached."""

    scenario_id: str
    attack_type: str
    attack_strength: float
    transactions: pd.DataFrame
    victim_cards: list[str] = field(default_factory=list)
    behavioral_changes: dict[str, object] = field(default_factory=dict)

    @property
    def spec(self) -> AttackSpec:
        return TAXONOMY[self.attack_type]

    @property
    def transaction_ids(self) -> list[str]:
        return self.transactions["transaction_id"].tolist()

    def metadata(self) -> dict[str, object]:
        """Structured metadata contract consumed by the API, UI and evaluator."""
        s = self.spec
        return {
            "scenario_id": self.scenario_id,
            "attack_type": self.attack_type,
            "attack_name": s.name,
            "category": s.category,
            "genai_role": s.genai_role,
            "mitre_atlas": s.atlas,
            "attack_strength": round(self.attack_strength, 3),
            "severity": s.severity,
            "hard_to_detect": s.hard_to_detect,
            "expected_detection_signals": list(s.expected_signals),
            "behavioral_changes": self.behavioral_changes,
            "synthetic_transaction_ids": self.transaction_ids,
            "n_transactions": len(self.transactions),
            "victim_cards": self.victim_cards,
            "ground_truth": "fraud",
            "synthetic": True,
        }


# --------------------------------------------------------------------------------------
# Simulation context
# --------------------------------------------------------------------------------------


class Ctx:
    """Shared state for building attack transactions against a synthetic population."""

    def __init__(self, pop, hist: pd.DataFrame, rng: np.random.Generator, tag: str = "atk"):
        self.pop = pop
        self.hist = hist
        self.rng = rng
        self.tag = tag
        self._n = 0
        self._extra: dict[str, dict] = {}
        # Attack traffic begins after the observed history, so temporal splits stay honest.
        self.t0: pd.Timestamp = (
            pd.Timestamp(hist["timestamp"].max()) if len(hist) else pd.Timestamp("2026-07-31")
        )
        self._cards = pop.cards.set_index("card_token")
        self._merch = pop.merchants
        g = hist.groupby("card_token")["amount"] if len(hist) else None
        self._med = g.median().to_dict() if g is not None else {}
        self._max = g.max().to_dict() if g is not None else {}
        # Per-card merchant history, needed by the mimicry attack to stay inside the
        # victim's own behavioural distribution.
        self._mer_by_card = (
            hist.groupby("card_token")["merchant_id"].apply(list).to_dict()
            if len(hist)
            else {}
        )

    # --- identifiers ---
    def txid(self) -> str:
        self._n += 1
        return f"{self.tag}_{self._n:07d}"

    def scenario(self, attack: str) -> str:
        return f"SCN-{attack}-{int(self.rng.integers(10_000, 99_999))}"

    # --- entity selection ---
    def victims(self, n: int) -> list[str]:
        toks = self.pop.cards["card_token"].to_numpy()
        n = min(n, len(toks))
        return list(self.rng.choice(toks, size=n, replace=False))

    def baseline(self, token: str) -> float:
        return float(self._med.get(token, 45.0))

    def peak(self, token: str) -> float:
        return float(self._max.get(token, 200.0))

    def card(self, token: str):
        # Accounts fabricated by an attack (synthetic-identity / deepfake-onboarding vectors)
        # live outside the legitimate population and have no transaction history.
        if token in self._extra:
            return self._extra[token]
        return self._cards.loc[token]

    def new_account(
        self,
        device: str | None = None,
        ip: str | None = None,
        ua: str | None = None,
    ) -> str:
        """Register a brand-new account with no history. Optionally share infrastructure."""
        i = int(self.rng.integers(0, 9_999_999))
        tok = f"tok_new_{i:07d}"
        d_dev, d_ip, d_ua = self.burner()
        country = str(self.rng.choice([c for c, _ in COUNTRIES]))
        self._extra[tok] = {
            "account_id": f"acct_new_{i:07d}",
            "issuer_country": country,
            "currency": CURRENCY_BY_COUNTRY[country],
            "primary_device": device or d_dev,
            "primary_ip_prefix": ip or d_ip,
            "ua_hash": ua or d_ua,
        }
        return tok

    def merchant(self, high_risk: bool | None = None, mcc: str | None = None) -> pd.Series:
        m = self._merch
        if mcc is not None:
            sub = m[m["mcc"] == mcc]
            if len(sub):
                m = sub
        elif high_risk is not None:
            sub = m[m["is_high_risk"] == high_risk]
            if len(sub):
                m = sub
        return m.iloc[int(self.rng.integers(0, len(m)))]

    def usual_merchant(self, token: str) -> pd.Series:
        """A merchant this card has genuinely used before (mimicry attacks need this)."""
        ids = self._mer_by_card.get(token)
        if not ids:
            return self.merchant()
        mid = ids[int(self.rng.integers(0, len(ids)))]
        hit = self._merch[self._merch["merchant_id"] == mid]
        return hit.iloc[0] if len(hit) else self.merchant()

    def fresh_merchant(self, mcc: str, age_days: int = 5) -> dict:
        """A merchant that does not exist in the population — a brand-new storefront."""
        i = int(self.rng.integers(0, 999_999))
        return {
            "merchant_id": f"mch_new_{i:06d}",
            "merchant_name": f"ShopFast-{i:05d}",
            "mcc": mcc,
            "merchant_country": str(self.rng.choice([c for c, _ in COUNTRIES])),
            "merchant_age_days": age_days,
        }

    def burner(self) -> tuple[str, str, str]:
        """Attacker-controlled device / network / user-agent triple."""
        i = int(self.rng.integers(0, 999_999))
        return (
            f"dev_atk_{i:06d}",
            f"{self.rng.integers(11, 223)}.{self.rng.integers(0, 255)}."
            f"{self.rng.integers(0, 255)}.0/24",
            f"ua_atk_{self.rng.integers(0, 999):03d}",
        )

    # --- row construction ---
    def row(
        self,
        token: str,
        ts: pd.Timestamp,
        amount: float,
        merchant: pd.Series | dict,
        attack_type: str,
        scenario_id: str,
        strength: float,
        *,
        device: str | None = None,
        ip: str | None = None,
        ua: str | None = None,
        channel: str = Channel.ECOM,
        entry_mode: str = EntryMode.ECOM_KEYED,
        card_present: bool = False,
        is_recurring: bool = False,
        avs: str = AvsResult.NO_MATCH,
        cvv: str = CvvResult.MATCH,
        three_ds: str = ThreeDsStatus.NOT_AUTHENTICATED,
        sca: str = ScaExemption.NONE,
        auth: str = AuthResponse.APPROVED,
        issuer_country: str | None = None,
    ) -> dict:
        c = self.card(token)
        m = merchant if isinstance(merchant, dict) else merchant.to_dict()
        d_dev, d_ip, d_ua = c["primary_device"], c["primary_ip_prefix"], c["ua_hash"]
        issuer = issuer_country or c["issuer_country"]
        m_country = m.get("merchant_country", issuer)
        return {
            "transaction_id": self.txid(),
            "timestamp": ts,
            "card_token": token,
            "account_id": c["account_id"],
            "issuer_country": issuer,
            "amount": round(float(amount), 2),
            "currency": c["currency"],
            "amount_local": round(float(amount), 2),
            "merchant_id": m["merchant_id"],
            "merchant_name": m["merchant_name"],
            "mcc": m["mcc"],
            "merchant_country": m_country,
            "merchant_age_days": int(m.get("merchant_age_days", 900)),
            "channel": channel,
            "entry_mode": entry_mode,
            "card_present": card_present,
            "is_recurring": is_recurring,
            "device_id": device or d_dev,
            "ip_prefix": ip or d_ip,
            "user_agent_hash": ua or d_ua,
            "avs_result": avs,
            "cvv_result": cvv,
            "three_ds_status": three_ds,
            "sca_exemption": sca,
            "network_token_used": entry_mode == EntryMode.NETWORK_TOKEN,
            "cross_border": m_country != issuer,
            "auth_response": auth,
            "is_fraud": 1,
            "attack_type": attack_type,
            "scenario_id": scenario_id,
            "attack_strength": round(float(strength), 3),
            "synthetic": True,
        }


def _frame(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=list(TRANSACTION_FIELDS))
    return pd.DataFrame(rows)[list(TRANSACTION_FIELDS)].sort_values(
        "timestamp", ignore_index=True
    )


def _scale(strength: float, lo: int, hi: int) -> int:
    """Map attack strength in [0,1] to a count in [lo,hi]."""
    return int(round(lo + (hi - lo) * float(np.clip(strength, 0.0, 1.0))))

