# Fraud Taxonomy

**Generated from `backend/app/attacks.py` — do not edit by hand.**
Regenerate with `.venv/bin/python scripts/gen_docs.py`.

**25 attack vectors across 10 categories.** Every vector has a working simulator, is mapped to MITRE ATLAS or ATT&CK, states what generative AI specifically changed about it, and declares the signals a competent detector ought to fire on.

## Why declared signals matter

Each vector's `expected_detection_signals` are ground truth for *detectability*, not just for the label. That lets the evaluation harness measure whether an attack was caught **for the right reason** rather than by coincidence — reported as per-signal recall in `artifacts/metrics.json`.

## Design principle: feasible-action attacks

The standing criticism of adversarial ML on tabular data is that it perturbs features an attacker cannot control. You cannot set `amount = 43.7291`, and you certainly cannot forge an EMV application transaction counter. Every attack here is restricted to the attacker's real action space:

| Attacker controls | Never forged |
|---|---|
| amount, timing, cadence | issuer-side verification results |
| merchant and MCC selection | cryptogram validity |
| channel, device, IP, user agent | transaction counters |
| which card is used, sequencing across cards | network token assurance level |

Where an attack *does* alter a verification field, it is because the real attack path genuinely produces that outcome — an intercepted OTP legitimately yields a 3-D Secure `AUTHENTICATED` status, which is precisely why OTP interception is dangerous.

## Safety boundary

Attacks are modelled purely as **observable behavioural change in a transaction stream** — the level a defender needs to build detection, and nothing lower. This repository contains no operational instructions for committing fraud. The simulator operates only on in-process synthetic data and imports no network capability; `backend/tests/test_security.py` proves this by parsing the modules with `ast`.

---

## Coverage summary

| Category | Vectors | Hard by design | Max severity |
|---|---|---|---|
| Account takeover | 3 | 1 | 5/5 |
| Adaptive evasion | 4 | 4 | 5/5 |
| Agentic commerce | 3 | 1 | 5/5 |
| Deepfake / KYC | 1 | 0 | 5/5 |
| Enumeration | 2 | 0 | 3/5 |
| First-party fraud | 1 | 1 | 3/5 |
| Fraud ring | 2 | 0 | 5/5 |
| Merchant fraud | 3 | 1 | 4/5 |
| Scam / social engineering | 3 | 3 | 5/5 |
| Synthetic identity | 3 | 1 | 5/5 |
| **Total** | **25** | **12** | — |

**Signal coverage:** 42 of 47 distinct expected signals are implemented as detectors (39 rule signals plus 3 emitted by the graph and text-safety stages).

Signals deliberately **not** implemented, and why — stated so per-signal recall is read honestly rather than looking like a silent miss:

- `graph_fanin` — emitted by the graph stage, not the rule stage
- `injection_pattern_in_text` — emitted by the text-safety stage
- `post_delivery_dispute` — requires dispute lifecycle data, outside the auth schema
- `refund_ratio_anomaly` — requires credit/refund messages, outside the auth schema
- `repeat_claimant_pattern` — requires dispute lifecycle data, outside the auth schema
- `ring_component` — emitted by the graph stage, not the rule stage
- `session_duress_pattern` — requires session/interaction telemetry, outside the auth schema
- `synchronised_timing` — covered in practice by ring_component + machine_cadence

---

## Vectors by category

### Account takeover

#### Voice-clone call-centre takeover

`VOICE_CLONE_ATO` · severity **5/5** · channels ECOM, MOTO

Support-channel takeover: contact details are changed, then spend follows from unfamiliar infrastructure while the account itself looks legitimate.

**What GenAI changed.** Seconds of sampled audio clone a cardholder's voice well enough to pass human and voice-biometric verification in a service call.

**Framework alignment.** ATLAS AML.T0015 Evade AI Model (voice biometric)

**Expected detection signals.** `device_change`, `geo_mismatch`, `profile_change_then_spend`, `behavioral_drift`

#### SIM-swap / OTP interception

`SIM_SWAP_OTP` · severity **5/5** · channels ECOM · **hard by design**

The strong-authentication step genuinely succeeds because the attacker controls the second factor. Verification fields look clean; behaviour does not.

**What GenAI changed.** Generated pretext scripts and cloned voices make carrier-side social engineering repeatable at scale.

**Framework alignment.** ATT&CK T1451 SIM Card Swap

**Expected detection signals.** `device_change`, `geo_mismatch`, `authenticated_but_anomalous`, `behavioral_drift`

#### Automated credential stuffing to takeover

`ATO_CREDENTIAL_STUFF` · severity **4/5** · channels ECOM

One operational footprint touches many unrelated accounts in a short window; successful sessions convert to spend.

**What GenAI changed.** Agentic browser automation solves challenges and adapts to varied login flows without bespoke scripting per target.

**Framework alignment.** ATT&CK T1110.004 Credential Stuffing

**Expected detection signals.** `device_sharing`, `ip_concentration`, `many_cards_one_device`, `machine_cadence`

### Adaptive evasion

#### Victim-profile mimicry

`ADAPTIVE_MIMICRY` · severity **5/5** · channels ECOM, POS · **hard by design**

The hardest case in this taxonomy: fraud that matches the victim's usual merchants, amounts, timing and device. Designed to be statistically near-invisible, so that residual detection must come from network structure rather than per-transaction anomaly.

**What GenAI changed.** A model fitted to the victim's own transaction history generates fraud drawn from the victim's legitimate behavioural distribution.

**Framework alignment.** ATLAS AML.T0043 Craft Adversarial Data

**Expected detection signals.** `beneficiary_concentration`, `subtle_drift`, `graph_fanin`

#### Velocity-threshold evasion

`VELOCITY_EVASION` · severity **4/5** · channels ECOM, POS · **hard by design**

The same total extraction, deliberately paced to stay under count and value velocity limits.

**What GenAI changed.** An adaptive agent infers effective thresholds from decline feedback and re-plans spacing automatically.

**Framework alignment.** ATLAS AML.T0015 Evade AI Model

**Expected detection signals.** `behavioral_drift`, `sub_threshold_pacing`, `device_change`

#### Low-value SCA exemption stacking

`SCA_EXEMPTION_ABUSE` · severity **4/5** · channels ECOM · **hard by design**

Extraction structured entirely beneath the low-value remote-payment exemption ceiling so that strong authentication is never triggered.

**What GenAI changed.** Automated planning keeps every authorisation inside an exemption envelope across merchants and time without manual bookkeeping.

**Framework alignment.** ATLAS AML.T0015 Evade AI Model

**Expected detection signals.** `sub_threshold_pacing`, `low_value_exemption_cluster`, `beneficiary_concentration`, `no_3ds_challenge`

#### Risk-analysis threshold gaming

`TRA_THRESHOLD_GAMING` · severity **4/5** · channels ECOM · **hard by design**

Amounts placed just inside the most permissive risk band, exploiting banded exemption logic rather than attacking the model directly.

**What GenAI changed.** Query-efficient probing maps a scoring boundary from accept/decline feedback alone, with no model access.

**Framework alignment.** ATLAS AML.T0043 Craft Adversarial Data

**Expected detection signals.** `sub_threshold_pacing`, `amount_just_below_band`, `exemption_claim_anomaly`

### Agentic commerce

#### Agent mandate replay / scope substitution

`MANDATE_REPLAY_ABUSE` · severity **5/5** · channels ECOM · **hard by design**

An authorisation whose merchant, amount or currency diverges from the cardholder's signed payment instruction — the failure mode that AP2 mandate signing and network-level instruction matching are explicitly designed to prevent.

**What GenAI changed.** Delegated-payment mandates are a brand-new artefact class; where signature scope or freshness is not fully enforced, a captured authorisation intent can be reused or re-pointed.

**Framework alignment.** ATT&CK T1550 Use Alternate Authentication Material

**Expected detection signals.** `mandate_mismatch`, `amount_just_below_band`, `machine_cadence`, `beneficiary_concentration`

#### Autonomous shopping-agent impersonation

`AGENT_IMPERSONATION` · severity **4/5** · channels ECOM

Fraudulent volume presented as legitimate delegated-agent commerce, at machine cadence and without human interaction rhythm.

**What GenAI changed.** As delegated AI agents legitimately transact on cardholders' behalf, attacker traffic can hide inside a brand-new and poorly-baselined traffic class.

**Framework alignment.** ATLAS AML.T0015 Evade AI Model

**Expected detection signals.** `machine_cadence`, `ua_homogeneity`, `no_human_session_rhythm`, `device_sharing`

#### Prompt injection via merchant-controlled fields

`AGENT_PROMPT_INJECTION` · severity **4/5** · channels ECOM

Adversarial instructions embedded in merchant descriptors, aimed at any downstream model that reads transaction text.

**What GenAI changed.** Merchant-supplied free text reaches LLM-based risk narration and agent reasoning, making the data plane an instruction channel.

**Framework alignment.** ATLAS AML.T0051 LLM Prompt Injection

**Expected detection signals.** `injection_pattern_in_text`, `new_merchant_risk`, `merchant_ticket_anomaly`

### Deepfake / KYC

#### Deepfake KYC onboarding bypass

`DEEPFAKE_KYC_ONBOARD` · severity **5/5** · channels ECOM

An account passes biometric onboarding via synthetic media, then monetises immediately — no history-building patience at all.

**What GenAI changed.** Real-time face swap and injection attacks defeat liveness checks that assume a camera observes a physical person.

**Framework alignment.** ATLAS AML.T0015 Evade AI Model (liveness/biometric model)

**Expected detection signals.** `new_account_velocity`, `immediate_high_value`, `high_risk_mcc`, `geo_mismatch`

### Enumeration

#### Micro-amount card testing

`CARD_TESTING_MICRO` · severity **3/5** · channels ECOM

Many candidate credentials validated with negligible-value authorisations before the viable ones are sold or used.

**What GenAI changed.** Agentic automation distributes probing across merchants and time to stay under per-merchant thresholds without human coordination.

**Framework alignment.** ATT&CK T1110 Brute Force

**Expected detection signals.** `micro_amount_cluster`, `many_cards_one_merchant`, `machine_cadence`, `auth_failure_ratio`

#### BIN range enumeration burst

`BIN_ENUMERATION_BURST` · severity **3/5** · channels ECOM

Sequentially related credentials probed in a tight burst, producing a distinctive decline signature.

**What GenAI changed.** Automated agents parallelise generation-and-test across BIN ranges and rotate infrastructure between bursts.

**Framework alignment.** ATT&CK T1110 Brute Force

**Expected detection signals.** `bin_sequence_pattern`, `auth_failure_ratio`, `machine_cadence`, `ip_concentration`

### First-party fraud

#### First-party dispute abuse

`FIRST_PARTY_DISPUTE` · severity **3/5** · channels ECOM · **hard by design**

The genuine cardholder transacts genuinely, then disputes after receiving value. Concentration appears per customer rather than per merchant.

**What GenAI changed.** Fluent, consistent dispute narratives are volume-produced, eroding the 'story quality' signal reviewers relied on.

**Framework alignment.** ATLAS AML.T0048 External Harms

**Expected detection signals.** `refund_ratio_anomaly`, `post_delivery_dispute`, `repeat_claimant_pattern`

### Fraud ring

#### Mule account fan-out

`MULE_FANOUT` · severity **5/5** · channels ECOM

Value from many compromised sources converges on a small beneficiary set. Invisible per-transaction; obvious as a graph.

**What GenAI changed.** Automated recruitment messaging scales mule acquisition, so the network layer grows faster than manual investigation can map it.

**Framework alignment.** ATLAS AML.T0048 External Harms

**Expected detection signals.** `beneficiary_concentration`, `graph_fanin`, `ring_component`, `rapid_pass_through`

#### Coordinated multi-card ring

`COORDINATED_RING` · severity **5/5** · channels ECOM, POS

Distinct cards linked by shared devices and network infrastructure, transacting in loose synchrony.

**What GenAI changed.** Coordination tooling lets a small crew operate many identities with consistent tradecraft and shared infrastructure.

**Framework alignment.** ATT&CK T1078 Valid Accounts

**Expected detection signals.** `device_sharing`, `ip_concentration`, `ring_component`, `graph_fanin`, `synchronised_timing`

### Merchant fraud

#### Fabricated merchant storefront

`FAKE_STOREFRONT` · severity **4/5** · channels ECOM

A newly registered merchant takes card-not-present volume at ticket sizes inconsistent with its declared category, then disappears before chargebacks land.

**What GenAI changed.** Generative tooling produces a complete, convincing storefront — copy, product imagery, reviews, policies — in minutes rather than weeks.

**Framework alignment.** ATLAS TA0002 Resource Development

**Expected detection signals.** `new_merchant_risk`, `merchant_ticket_anomaly`, `avs_failure`, `high_risk_mcc`

#### Transaction laundering / MCC misrepresentation

`TRANSACTION_LAUNDERING` · severity **4/5** · channels ECOM · **hard by design**

Volume for a prohibited or high-risk category is presented under a benign MCC, so category-based controls never engage.

**What GenAI changed.** Automated content generation sustains many plausible front-shop facades concurrently, each masking the same underlying prohibited activity.

**Framework alignment.** ATLAS AML.T0048 External Harms

**Expected detection signals.** `mcc_inconsistency`, `merchant_ticket_anomaly`, `cross_border`, `beneficiary_concentration`

#### Collusive refund and credit abuse

`REFUND_ABUSE_COLLUSION` · severity **3/5** · channels ECOM

Purchases are followed by disproportionate credits to a small beneficiary set, extracting value through the refund rail rather than the purchase rail.

**What GenAI changed.** LLM-drafted dispute narratives industrialise claim submission and tune wording against known adjudication criteria.

**Framework alignment.** ATLAS AML.T0048 External Harms

**Expected detection signals.** `refund_ratio_anomaly`, `beneficiary_concentration`, `device_sharing`

### Scam / social engineering

#### LLM-driven authorised push payment scam

`APP_SCAM_LLM` · severity **5/5** · channels ECOM · **hard by design**

The genuine cardholder, on their genuine device, willingly authorises the payment. Every credential signal is clean — only intent is wrong.

**What GenAI changed.** Conversational models sustain thousands of individually tailored, emotionally coherent grooming conversations at once.

**Framework alignment.** ATT&CK T1566 Phishing (payment-directed variant)

**Expected detection signals.** `first_time_beneficiary`, `amount_spike_vs_baseline`, `session_duress_pattern`, `authenticated_but_anomalous`

#### Escalating investment / romance scam

`ROMANCE_PIG_BUTCHERING` · severity **5/5** · channels ECOM · **hard by design**

A slow escalation of victim-authorised transfers toward one beneficiary cluster over days or weeks. Each single payment looks defensible.

**What GenAI changed.** Persistent AI personas maintain long-horizon relationships and adapt escalation pacing to each victim's resistance.

**Framework alignment.** ATT&CK T1566 Phishing

**Expected detection signals.** `escalating_amount_sequence`, `beneficiary_concentration`, `first_time_beneficiary`, `behavioral_drift`

#### Invoice redirection / business email compromise

`INVOICE_REDIRECT_BEC` · severity **4/5** · channels ECOM, MOTO · **hard by design**

A high-value payment to a newly substituted beneficiary, structurally identical to a routine supplier settlement.

**What GenAI changed.** Models mimic a specific counterparty's writing style and thread history, removing the linguistic tells staff are trained to spot.

**Framework alignment.** ATT&CK T1566.002 Spearphishing Link

**Expected detection signals.** `first_time_beneficiary`, `amount_spike_vs_baseline`, `corporate_exemption_abuse`, `beneficiary_concentration`

### Synthetic identity

#### Synthetic identity bust-out

`SYNTH_ID_BUSTOUT` · severity **5/5** · channels ECOM, POS

After the build-up phase, the identity spends to exhaustion in a short window across high-liquidity categories, then goes dark.

**What GenAI changed.** Generative tooling scales the number of aged identities available to burn simultaneously, turning bust-out from artisanal to industrial.

**Framework alignment.** ATLAS AML.T0048 External Harms / Financial Harm

**Expected detection signals.** `amount_spike_vs_baseline`, `high_risk_mcc`, `velocity_burst`, `credit_limit_exhaustion`

#### Synthetic identity history building

`SYNTH_ID_BUILDUP` · severity **4/5** · channels ECOM, POS · **hard by design**

Freshly minted synthetic accounts transact small and clean to accrue a credible history before monetisation. Individually unremarkable by design.

**What GenAI changed.** LLMs mass-produce coherent applicant personas and plausible life-event narratives, so an identity survives manual review that would previously have caught it.

**Framework alignment.** ATLAS TA0002 Resource Development (persona fabrication)

**Expected detection signals.** `new_account_velocity`, `thin_history`, `device_sharing`

#### Generated-document application farm

`GENAI_DOC_FARM` · severity **4/5** · channels ECOM

A large batch of accounts onboarded from one operational footprint. The documents are unique but the infrastructure is not.

**What GenAI changed.** Image models produce unlimited passable identity documents and selfies; the bottleneck moves from document production to infrastructure reuse.

**Framework alignment.** ATLAS TA0002 Resource Development

**Expected detection signals.** `device_sharing`, `ip_concentration`, `ua_homogeneity`, `new_account_velocity`

---

## Simulator coverage

All 25 vectors have an executable simulator. `backend/tests/test_data_pipeline.py` parameterises over the full taxonomy, so a vector without a working simulator fails the build.

```bash
# simulate every vector and print a summary
.venv/bin/python -m backend.app.attacks
```
