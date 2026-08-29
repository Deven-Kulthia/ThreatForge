# Threat Landscape — GenAI-Powered Payment Fraud (2024–2026)

**Status:** Phase 1 complete. Last updated 2026-08-17.
**Evidence rule:** every statistic carries a source URL that was actually retrieved. Claims that
could not be verified are marked `[UNCERTAIN]` or `[NOT FOUND]` and must not be used in the deck.
**Retrieval caveat:** mastercard.com, ukfinance.org.uk, entrust.com and europol.europa.eu refused
automated fetches; UK Finance / Europol IOCTA / ECB card-fraud figures are therefore absent rather
than dismissed.

---

## 1. Headline anchors (use these in the deck)

| Metric | Value | Source |
|---|---|---|
| FBI IC3 2025 total | **1,008,597 complaints · $20.877B losses · +26% YoY** | ic3.gov 2025 Annual Report |
| Cyber-enabled fraud share | 452,868 complaints · **$17.697B = 85% of all losses** | same |
| **Explicit AI nexus (2025)** | **22,364 complaints · $893,346,472 losses** | same |
| BEC 2025 | $3,046,598,558 over 24,768 complaints; **$30.26M explicitly AI-involved** | same |
| Investment fraud w/ AI nexus | **>$632M** (of $8.649B total investment losses) | same |
| Romance w/ AI nexus | >$19M · voice-clone distress scams >$5M | same |
| Projected GenAI fraud losses (US) | **$12.3B (2023) → $40B by 2027, 32% CAGR** | Deloitte CFS |
| Contact-centre fraud | **$12.5B lost in 2024 across 2.6M fraud events** | Pindrop Voice Intelligence Report |
| iOS injection attacks | **+1,151% YoY, H2 2025** | iProov |
| Illicit crypto inflows | **≥$154B in 2025, +162% YoY; 84% in stablecoins** | Chainalysis 2026 Crypto Crime Report |

> **`[A]` Framing for the deck:** the single most defensible one-liner is that **85% of a
> $20.9B loss pool is cyber-enabled**, and the AI-attributed slice is already **$893M and
> newly measurable**. That establishes urgency without overclaiming — we cite the AI figure
> as *explicitly attributed*, not as the total AI-driven loss.

## 2. Threat categories → observable signals

Condensed to what changes a detection decision. Full source list in `research-sources.md`.

### 2.1 AI-generated social engineering (phishing / vishing / smishing / BEC)
- **What GenAI changed:** removes the grammar/style tell that filters and staff training relied
  on; per-victim personalisation at population scale; cheap translation opens any market;
  embedded chatbots sustain conversation without human operators. `[V]` FBI IC3 PSA I-120324
- **Signals:** new-beneficiary + bank-detail-change on invoices · mailbox forwarding rules set
  before a payment instruction · urgency language + out-of-band channel switch · template reuse
  with entity substitution across recipients.
- **Rail mix:** BEC is ~72% wire/ACH; investment scams ~86% crypto. `[V]` IC3 2025

### 2.2 Deepfake-assisted fraud and KYC defeat
- **Critical shift:** the dominant surface moved from **presentation** attacks (replaying media to
  a genuine camera) to **injection** attacks (synthetic frames introduced into the capture
  pipeline via virtual cameras/emulators/modified clients) — because injection **scales and
  automates**. `[V]` iProov
- **Signals — FinCEN's own red-flag list** `[V]` FIN-2024-Alert004: inconsistencies across
  submitted documents · inability to authenticate income/identity · applicant reporting repeated
  "technical glitches" or asking to switch verification channel mid-check · third-party webcam
  plugins / virtual capture devices · post-onboarding: IP inconsistent with profile, coordinated
  activity across similar accounts, high chargeback volume, rapid transactions on new accounts,
  immediate withdrawal to crypto/gambling rails.
- **Documented case:** one individual opened **46 fraudulent ABN AMRO accounts** via mobile
  onboarding using deepfaked selfies matched to stolen IDs. `[V]` iProov, 2026-04-24
- `[UNCERTAIN]` Claim that NIST SP 800-63-4 makes injection-attack detection a mandatory control
  objective — asserted by a vendor, not verified against NIST. **Do not cite.**

### 2.3 Synthetic identity
- **What GenAI changed:** the two historical bottlenecks — a plausible document image and a
  matching face — are now cheap and unlimited, so identity *manufacturing* scales to portfolio
  size. FinCEN confirms rising SAR volume describing GenAI-altered or fully synthetic ID images,
  sometimes combined with stolen real PII. `[V]` FIN-2024-Alert004
- **Signals:** implausible file inception for the SSN/DOB pair · one device/behavioural
  fingerprint across many "distinct" applicants · identical document capture artefacts ·
  utilisation ramp then synchronised maximum draw · mass disputes against legitimate tradelines
  (credit washing).
- **Stat (US auto lending, Q3 2018 → Q3 2025):** synthetic **$93M → $208M**; first-party
  **$88M → $323M**; third-party **$18M → $47M**. `[V]` TransUnion, July 2026

### 2.4 Account takeover
- **What GenAI changed:** hyper-personalised OTP-elicitation pretexts; automation of large-scale
  credential attacks; deepfake audio aimed at call-centre authentication and **account-recovery
  paths** — the weakest identity link once device/session controls harden.
- **Signals:** **telco-product takeover preceding bank ATO** · device rebinding/re-enrolment
  velocity · behavioural divergence from the account's **own** baseline (not a population
  baseline) · MFA-prompt-fatigue patterns · new payee + limit increase + channel change in one session.
- **Stat:** UK Cifas — facility takeover **18% of all fraud filings (+5%)**; identity fraud 54%
  (+9%); misuse of facility 24%. Cifas explicitly attributes takeover growth to AI-enhanced
  communications, **deepfake audio targeting call centres**, and SIM hijacking. `[V]` Fraudscape 2026

### 2.5 APP fraud, romance / pig butchering
- **What GenAI changed:** LLMs sustain thousands of individually distinct grooming conversations
  in any language, **decoupling scam throughput from headcount**; AI-generated celebrity/CEO video
  underwrites fake investment "clubs". `[V]` IC3 2025
- **Signals:** long low-value trust transfers escalating to liquidation of savings/credit ·
  victim-side evidence of remote coaching · payment-narrative mismatch · receiving-side
  concentration into a few newly onboarded accounts · crypto off-ramp within hours.
- **UK regime (highly relevant to commercial framing):** mandatory reimbursement live
  **7 Oct 2024**. Since then **438,300 claims, 301,500 in scope, 88% (£316m) of reimbursable
  value repaid**; Q1 2026 alone £72.6m (89%). Only ~**2–3%** of claims rejected for insufficient
  consumer caution. `[V]` PSR dashboard, Q1 2026
- > **`[A]` This is the commercial-viability argument.** Reimbursement liability makes scam
  > detection a direct P&L line for issuers, not a goodwill exercise. APP/scam detection is
  > where our closed loop has the clearest buyer.

### 2.6 Fake merchants, transaction laundering, refund abuse
- **What GenAI changed:** storefront copy, product imagery, reviews, policy pages and brand
  assets generated in minutes → disposable merchant identities are cheap and stylistically clean.
  AI-written dispute narratives raise the quality floor of illegitimate claims.
- **Signals:** descriptor vs website/product mismatch · MCC-atypical ticket-size and geography
  distributions · shared infrastructure/registrant/payout-account linkage across "unrelated"
  merchants · volume onset with no marketing footprint · refund-to-sale ratio and repeat-claimant
  graphs · disputes clustered on one reason code.
- **Stats `[V]` vendor-sourced, label as such:** 83.4% of merchants reported increased
  friendly-fraud chargebacks in 2024; consumers filed >$37.07B in disputes; merchants win 44.6%
  of represented disputes but net only 10.7% recovery (Chargebacks911). Ecommerce chargeback rates
  +222% Q1 2023→Q1 2024 (Sift). `[NOT FOUND]` hard transaction-laundering volume estimate.

### 2.7 Agentic commerce — the genuinely new surface
**The protocols are real and verified (2026-08-17):**

| Standard | Status | Trust mechanism |
|---|---|---|
| **Google AP2** | Announced 2025-09-17, **60+ orgs** incl. Mastercard, Amex, PayPal, Adyen, Worldpay, Forter, Coinbase, JCB, Revolut, UnionPay | Cryptographically signed **Mandates** as verifiable credentials → non-repudiable audit trail. Now **Checkout Mandate + Payment Mandate**; **v0.2 donated to the FIDO Alliance** |
| **Visa Intelligent Commerce** | In development | Agent-specific pass-through tokens, passkey step-up, **network-level checks that authorizations match the user's authenticated Payment Instruction** |
| **Visa Trusted Agent Protocol** | In development | Merchant-specific, purpose-bound, time-bound signatures that "cannot be replayed or relayed" |
| **Agentic Commerce Protocol (ACP)** | Stripe + OpenAI, Apache-2.0 | REST/MCP checkout spec, Stripe Shared Payment Token, merchant stays merchant of record |
| **x402** | Linux Foundation **x402 Foundation** | HTTP-402-native chain-agnostic stablecoin payments. Self-reported 75.41M txns / $24.24M trailing 30d — **unaudited, do not cite as fact** |
| **Mastercard Agent Pay** | Real (April 2025 announcement); Mastercard is also an AP2 collaborator | `[V]` via secondary sources only — mastercard.com blocked all fetches |

- **Threat mechanics:** agent **impersonation** (unsigned automation claiming to be a trusted
  agent) and its inverse (legitimate agents blocked as bots) · **prompt injection** via hostile
  product page / review / email / tool output steering an agent's purchase, recipient or amount
  (OWASP **LLM01:2025**, compounded by **LLM06:2025 Excessive Agency**) · **mandate/scope abuse**
  (replay, amount or merchant substitution) — precisely what mandate signing and VisaNet
  instruction-matching exist to prevent.
- **Signals:** absence of signed-agent attestation on agent-claimed traffic · authorization
  details diverging from the signed instruction (merchant/amount/currency) · inhumanly consistent
  inter-action timing · one credential fanned across many merchants in seconds · agent sessions
  with no prior consumer-recognition signals.
- **Stat:** AI "user action" crawling grew **>15× in 2025**; non-Google AI bots at 4.2% of HTML
  request traffic; Cloudflare now runs a Verified Bots / Signed Agents directory. `[V]` Cloudflare Radar 2025
- > **`[A]` Strategic significance:** Mastercard is a named AP2 collaborator and ships Agent Pay.
  > An attack vector aimed at **mandate abuse and agent impersonation** is therefore directly
  > relevant to Mastercard's own roadmap — the strongest possible answer to "relevance to live
  > payments." Almost no hackathon entrant will cover it.

### 2.8 Fraud rings and mule networks
- **Signals:** synchronised inbound/outbound timing across unrelated accounts · same-day in-and-out
  to hard-to-reverse rails · shared device/behavioural fingerprints across "independent" customers
  · sudden inbound velocity on dormant young accounts.
- **Stats:** Cifas added a dedicated **"funds received – money mule"** filing reason in 2025;
  mule-indicative behaviour in **company accounts +85%**; largest rises +73%/+75% in under-30 and
  31–40 age bands. `[V]` Fraudscape 2026. Crypto **laundering-as-a-service** networks now serve
  scam compounds. `[V]` Chainalysis

### 2.9 Card testing / enumeration
- `[UNCERTAIN]` The enabling shift is automation and CAPTCHA-solving economics rather than LLMs
  specifically. No primary source quantifies a GenAI contribution — **do not claim one.**
- **Signals:** spike in failed/blocked authorizations and generic declines · low-amount payments
  with nonsensical name/email · many cards attached to few accounts, or many accounts from one IP ·
  rising authorization volume with collapsing approval rate. Consequence: **lasting issuer-side
  decline-rate damage to the merchant even after the attack stops.** `[V]` Stripe docs
- `[NOT FOUND]` Network-published enumeration volume/loss figures; Visa VAMP thresholds unverified.

### 2.10 First-party fraud
- **What GenAI changed:** dispute and hardship narratives are fluent, consistent and
  volume-produced, eroding the "story quality" signal; social diffusion normalises the behaviour.
- **Signals:** "item not received" concentration **by customer, not by merchant** · disputes filed
  after full product use or confirmed digital delivery · first-payment default with clean
  application data · repeat claimants across a consortium.
- **Stats:** Cifas — "falsely reporting a loss" **+189%** on bank accounts, amid "growing evidence
  around the normalisation of first-party fraud" `[V]`; TransUnion auto first-party **$88M → $323M** `[V]`.

## 3. What this implies for our build `[A]`

1. **Mastercard's four named threats are all covered** by verified evidence above: synthetic
   identities (§2.3), deepfake KYC (§2.2), fake merchant storefronts (§2.6), AI-enabled scams (§2.5).
2. **The highest-value signal family is behaviour-vs-own-baseline, not population anomaly.** ATO,
   APP scams and mimicry all present clean credentials; only deviation from the entity's own
   history or from network structure exposes them.
3. **Scam/APP detection is where clean credentials meet real liability** (UK reimbursement regime).
   Our system should treat "genuine device, genuine authentication, wrong intent" as a first-class
   case — most detectors implicitly assume compromised credentials.
4. **Agentic commerce is the differentiator.** Real standards, Mastercard participation, an
   articulated threat model, and near-zero hackathon coverage.
5. **Injection > presentation** is the sophisticated framing for deepfake KYC, and it maps to
   observable post-onboarding transaction behaviour, which is what we can actually simulate.
