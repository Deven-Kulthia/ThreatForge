# Threat Model

Two distinct threat models, kept separate because they answer different questions:

1. **§1 — The payment ecosystem** we are defending. Who attacks payments, with what
   GenAI-era capabilities, and what we can observe.
2. **§2 — Aegis itself** as a system under attack. What an adversary could do to our
   detector, and what we do about it.

Full evidence base with citations: [`../research/threat-landscape.md`](../research/threat-landscape.md).
Attack catalogue: [`fraud-taxonomy.md`](fraud-taxonomy.md).

---

# §1 — Threat model: payments

## 1.1 What changed

GenAI did not invent payment fraud. It removed the three constraints that used to limit it:

| Constraint before | Removed by | Consequence |
|---|---|---|
| Convincing text required fluency and effort | LLMs | Per-victim personalisation at population scale; the grammar tell that filters relied on is gone |
| A convincing face/voice required skill | Generative media | Deepfake KYC and voice-clone call-centre takeover become commodity attacks |
| Scam throughput was bounded by headcount | Conversational agents | Thousands of simultaneous grooming conversations, decoupled from operator count |

Measured: FBI IC3 recorded **$20.877B** in 2025 losses (+26% YoY), of which **85%** is
cyber-enabled, with **$893M** explicitly attributed to an AI nexus. Deloitte projects US
GenAI-enabled fraud rising from **$12.3B (2023) to $40B by 2027**.

## 1.2 Actors and capability

| Actor | Capability | Primary vectors |
|---|---|---|
| **Opportunistic individual** | Off-the-shelf generative tools, no infrastructure | First-party dispute abuse, refund abuse |
| **Organised ring** | Shared infrastructure, mule networks, industrial identity manufacturing | Synthetic identity bust-out, mule fan-out, coordinated multi-card rings |
| **Scam compound** | Persistent AI personas, long-horizon social engineering, off-ramps | APP scams, romance/pig-butchering, investment fraud |
| **Automation operator** | Agentic browser automation, CAPTCHA economics, credential lists | Credential stuffing, card testing, BIN enumeration |
| **Sophisticated adversary** | Adaptive probing, threshold inference from decline feedback | Velocity evasion, SCA exemption stacking, risk-band gaming, victim-profile mimicry |
| **Agentic-commerce abuser** | Impersonation of delegated payment agents; injection into agent context | Agent impersonation, mandate replay, prompt injection via merchant fields |

## 1.3 Mastercard's four named priority threats

The challenge announcement names four explicitly. All four are covered:

| Named threat | Our vectors |
|---|---|
| Synthetic identities | `SYNTH_ID_BUILDUP`, `SYNTH_ID_BUSTOUT`, `GENAI_DOC_FARM` |
| Deepfake KYC | `DEEPFAKE_KYC_ONBOARD`, `VOICE_CLONE_ATO` |
| Fake merchant storefronts | `FAKE_STOREFRONT`, `TRANSACTION_LAUNDERING`, `REFUND_ABUSE_COLLUSION` |
| AI-enabled scams | `APP_SCAM_LLM`, `ROMANCE_PIG_BUTCHERING`, `INVOICE_REDIRECT_BEC` |

## 1.4 The hardest case: clean credentials, wrong intent

Most detection implicitly assumes compromised credentials — an unfamiliar device, a failed
verification, an anomalous geography. Three of our vectors deliberately break that
assumption:

| Vector | Why every credential signal is clean |
|---|---|
| `APP_SCAM_LLM` | The genuine cardholder authorises on their own device with real 3-D Secure |
| `SIM_SWAP_OTP` | The attacker *holds* the second factor, so authentication genuinely succeeds |
| `ADAPTIVE_MIMICRY` | Fraud drawn from the victim's own merchants, amounts, timing and device |

**Detection consequence.** For this class, the only remaining signals are deviation from the
entity's *own* behavioural baseline and network structure. This is why the feature layer
prioritises per-entity baselines over population anomalies, and why the graph stage exists
at all. It is also why we report a signal named `authenticated_but_anomalous` — strong
authentication succeeding is not evidence of legitimacy.

Commercially, this is where the money is: under the UK reimbursement regime (live 7 Oct
2024), **88% of reimbursable APP scam value — £316m — has been repaid**, making scam
detection a direct P&L line for issuers rather than a goodwill exercise.

## 1.5 Emerging surface: agentic commerce

The rails are real and Mastercard is a participant — Agent Pay and Agentic Tokens (Apr 2025),
Agent Pay for Machines (Jun 2026), and collaboration on Google's AP2 (60+ organisations,
v0.2 donated to the FIDO Alliance). Visa ships Intelligent Commerce and a Trusted Agent
Protocol.

Three threats follow, and the defensive tooling does not yet exist:

1. **Agent impersonation** — unsigned automation claiming to be a trusted agent, hiding
   inside a brand-new and poorly-baselined traffic class.
2. **Mandate abuse** — an authorization whose merchant, amount or currency diverges from the
   cardholder's signed instruction. This is precisely the failure mode AP2's signed mandates
   and Visa's network-level instruction matching exist to prevent.
3. **Prompt injection through the data plane** — merchant-controlled text reaching an agent
   or a risk-narration model (OWASP LLM01, compounded by LLM06 Excessive Agency).

Observable signals we model: absence of signed-agent attestation, machine-regular cadence
with zero jitter, one credential fanned across many merchants in seconds, homogeneous client
fingerprints, and authorization details diverging from the signed instruction.

## 1.6 Out of scope, stated

Aegis models the **authorization message layer**. Deliberately outside scope:

- KYC/onboarding media forensics (liveness, injection-attack detection) — we model the
  *post-onboarding transaction behaviour* that follows a defeated check, not the image
  pipeline
- Dispute lifecycle and refund rails — hence four declared signals we cannot emit
- Session and device telemetry (keystroke/swipe dynamics) — data-collection cost
- Card-not-present e-commerce web-layer defences (bot management, WAF)
- Cryptographic attacks on EMV or tokenization

---

# §2 — Threat model: Aegis itself

Treating our own detector as an attack surface. This section is the reason four adaptive
vectors exist in the taxonomy.

## 2.1 Evasion — the primary threat

An adversary who observes accept/decline outcomes can infer thresholds without any model
access. Four vectors implement this within feasible action bounds:

| Vector | Mechanism | Mitigation, and its limits |
|---|---|---|
| `VELOCITY_EVASION` | Paces extraction under count/value limits | Multi-horizon velocity (1h/24h/7d) plus per-entity baseline; a sufficiently patient attacker still degrades detection |
| `SCA_EXEMPTION_ABUSE` | Keeps every authorization under the PSD2 low-value ceiling | `band_proximity` + `low_value_exemption_cluster` catch the *pattern* even when each payment is compliant |
| `TRA_THRESHOLD_GAMING` | Sits just inside the most permissive risk band | `amount_just_below_band`; this attacks banded exemption *logic*, not the model, so the real fix is policy-side |
| `ADAPTIVE_MIMICRY` | Generates fraud from the victim's own distribution | Deliberately near-invisible per transaction; residual detection must come from network structure. **Our weakest recall, reported as such** |

**Honest statement:** these are mitigations, not solutions. Recall on the adaptive vectors
is materially lower than on the crude ones, and `evaluate.py` reports per-attack recall
worst-first so this is visible rather than buried in an average.

## 2.2 Concept drift — partly invisible by proof

Label-free drift monitoring detects covariate shift reliably, but **pure concept drift with
unchanged P(X) is structurally invisible** — "exactly zero delta", replicated in two
independent 2026 papers.

This is the rigorous argument for why a generator is necessary rather than decorative: if a
class of change cannot be detected by monitoring, the only way to know your detector has
gone blind is to *generate* that change and test. Aegis can produce exactly that case.

## 2.3 Label feedback poisoning — named, not solved

A deployed detector poisons its own future labels: blocked transactions never resolve, so
they never become confirmed fraud or confirmed legitimate. The evaluation models
**label delay** (the 5% delay block between train and test) but does not solve the feedback
loop. The literature flags this as an open gap, and we do not claim otherwise.

## 2.4 Poisoning and model theft

| Threat | Assessment |
|---|---|
| Training-data poisoning | No external poisoning surface in the demo — training data is generated in-process. A production deployment ingesting real traffic would need drift and integrity monitoring |
| Model extraction | No score is exposed to an unauthenticated caller in a production posture; in the demo the API is localhost-only |
| Adversarial perturbation transfer | Gradient-based perturbations on tabular fraud models transfer across model families, so an ensemble is not automatic protection. Our cascade mitigates partly by combining deterministic rules with a learned model — rules have no gradient to follow |

## 2.5 Attacks on the AI layer itself

| Threat | Position |
|---|---|
| Prompt injection via merchant text | Screened and contained; demonstrated live (`AGENT_PROMPT_INJECTION`) |
| Excessive agency | No LLM has tool access or decision authority |
| LLM-as-judge manipulation | We do not use an LLM as evaluator; all metrics are computed |
| Explanation gaming | Reason codes derive from deterministic rules and exact arbiter coefficients, not from a generative model that could be steered |

## 2.6 Residual risk register

| # | Risk | Severity | Status |
|---|---|---|---|
| R1 | Adaptive mimicry evades per-transaction detection | High | Partially mitigated by graph structure; recall reported honestly |
| R2 | Pure concept drift invisible to monitoring | High | Acknowledged with citation; the generator exists to compensate |
| R3 | Label feedback poisoning in deployment | Medium | Named limitation; delay modelled, loop unsolved |
| R4 | Synthetic data may not transfer to live distributions | Medium | Schema built to real message standards; prevalence sensitivity stated in metrics |
| R5 | No authentication on the API | Medium | Scope decision for a local demo; documented in `security.md` §5 |
| R6 | Threshold gaming is a policy problem, not a model problem | Medium | Signalled by `band_proximity`; real fix is exemption policy |
| R7 | Audit trail is not tamper-evident | Low | Append-only by convention; hash-chaining noted as production work |
