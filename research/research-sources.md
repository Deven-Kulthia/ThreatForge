# Research Sources

Consolidated source register for Phase 1. Only URLs actually retrieved are listed as verified.
Retrieval date **2026-08-17** unless stated. Tooling note: WebSearch was unavailable on this
model; research agents used direct URL fetches, the arXiv API, sitemap harvesting and Google
News RSS. Several sites (mastercard.com, ukfinance.org.uk, entrust.com, europol.europa.eu, G2,
Gartner Peer Insights, TrustRadius, Kaggle license sidebars) blocked automated access — gaps are
recorded as `[NOT FOUND]` rather than filled by inference.

## 1. Competition (authoritative)
| Source | URL |
|---|---|
| Kaggle competition — Overview | https://www.kaggle.com/t/4926910fda5e404aa49abd61fee21913 |
| Kaggle competition — Rules tab (Mastercard T&C + Privacy Notice + Kaggle Foundational Rules) | same page, Rules tab |
| Luma event page | https://luma.com/kyz978xv |
| LinkedIn announcement (Mastercard AI Garage) | https://www.linkedin.com/posts/mastercard-ai-garage_mastercard-gff2026-globalfintechfest-activity-7493274878331101184-vLJM |
| Global Fintech Fest 2026 | https://www.globalfintechfest.com/ |

Local captures: `research/kaggle-raw/overview.txt`, `research/kaggle-raw/rules.txt`.

## 2. Threat intelligence — primary/regulator
- FBI IC3 2025 Annual Report — https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf
- FBI PSA I-120324, GenAI-facilitated financial fraud — https://www.ic3.gov/PSA/2024/PSA241203
- FinCEN Alert FIN-2024-Alert004, deepfake media (2024-11-13) — https://www.fincen.gov/sites/default/files/shared/FinCEN-Alert-DeepFakes-Alert508FINAL.pdf
- UK PSR APP scams reimbursement dashboard (Q1 2026) — https://www.psr.org.uk/information-for-consumers/app-scams-reimbursement-dashboard/
- Cifas Fraudscape 2026 — https://www.fraudscape.co.uk
- EU Commission Delegated Regulation 2018/389 (PSD2 RTS, SCA exemptions Art. 11–18, Annex fraud-rate bands) — https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32018R0389
- `[NOT FOUND]` UK Finance Annual Fraud Report · Europol IOCTA 2025 · ECB card fraud report · Visa/Mastercard enumeration statistics · FTC 2025 full-year totals

## 3. Threat intelligence — industry
- Deloitte CFS, deepfake banking fraud risk — https://www.deloitte.com/us/en/insights/industry/financial-services/deepfake-banking-fraud-risk-on-the-rise.html
- Pindrop Voice Intelligence & Security Report — https://www.pindrop.com/reports/voice-intelligence-security-report
- iProov, deepfake KYC / injection attacks / ABN AMRO case — https://www.iproov.com/blog/deepfake-bank-account-kyc-account-fraud-abn-amro
- TransUnion auto-lending fraud losses (July 2026) — https://newsroom.transunion.com/auto-loan-fraud-losses-more-than-triple-in-key-categories-new-transunion-analysis-finds/
- Chainalysis 2026 Crypto Crime Report — https://www.chainalysis.com/blog/2026-crypto-crime-report-introduction/
- Chargebacks911 chargeback statistics — https://chargebacks911.com/chargeback-stats/
- Cloudflare Radar 2025 Year in Review (AI bot traffic) — https://blog.cloudflare.com/radar-2025-year-in-review/
- Stripe card-testing prevention docs — https://docs.stripe.com/disputes/prevention/card-testing

## 4. Agentic commerce standards
- Google AP2 announcement — https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol
- AP2 protocol site — https://ap2-protocol.org/
- Visa Intelligent Commerce — https://developer.visa.com/capabilities/visa-intelligent-commerce
- Visa Trusted Agent Protocol — https://developer.visa.com/capabilities/trusted-agent-protocol
- Agentic Commerce Protocol (Stripe + OpenAI, Apache-2.0) — https://www.agenticcommerce.dev/
- x402 / x402 Foundation — https://www.x402.org/
- Mastercard Agent Pay — `[V via secondary]` https://en.wikipedia.org/wiki/Agentic_commerce (mastercard.com blocked)

## 5. Detection methodology — benchmarks & critiques
- **GADBench** (trees + neighbour aggregation beat tailored GNNs) — https://arxiv.org/abs/2306.12251
- **GAD in the Wild** (GNNs collapse to zero recall at scale) — https://arxiv.org/abs/2605.07133
- ADBench — https://arxiv.org/abs/2206.09426
- Deep AD no edge over shallow — https://arxiv.org/abs/2507.12295
- Trees still beat DL on tabular — https://arxiv.org/abs/2207.08815 · https://arxiv.org/abs/2106.03253
- Multi-scale graph: tabular baselines hard to beat — https://arxiv.org/abs/2603.14592
- Sequence embeddings add nothing over GBDT (NICE Actimize) — https://arxiv.org/abs/2605.21490
- TabTransformer — https://arxiv.org/abs/2012.06678
- Soft/hard identity links, 25M-node production graph — https://arxiv.org/abs/2512.19061
- GraphSAGE ring recovery benchmark — https://arxiv.org/abs/2604.21093
- Money-mule prioritisation with GraphSAGE — https://arxiv.org/abs/2509.12255
- PromoGuardian production results — https://arxiv.org/abs/2510.12652
- Behavioural drift (97% → 1.78% over 26 months) — https://arxiv.org/abs/2502.20359
- Swipe continuous auth — https://arxiv.org/abs/2606.11457 · keystroke EER — https://arxiv.org/abs/2607.24747 · https://arxiv.org/abs/2509.24807
- No fraud paper reports latency/cost/calibration — https://arxiv.org/abs/2607.13078

## 6. Imbalance, calibration, evaluation
- SMOTE/RUS not recommended — https://arxiv.org/abs/2605.14147
- SMOTE-before-split leakage — https://arxiv.org/abs/2603.22752
- SMOTE and multimodal minority — https://arxiv.org/abs/2607.19153 · https://arxiv.org/abs/2607.25413
- Capacity-adjusted metrics — https://arxiv.org/abs/2605.03289
- Resampling vs calibration (RUS: ECE 0.008 → 0.395) — https://arxiv.org/abs/2606.29720
- Isotonic + conformal risk control — https://arxiv.org/abs/2605.24696
- Predictive multiplicity in credit risk — https://arxiv.org/abs/2603.11750
- PR vs ROC under imbalance — Saito & Rehmsmeier, PLOS ONE 2015, https://doi.org/10.1371/journal.pone.0118432 · Davis & Goadrich, ICML 2006, https://doi.org/10.1145/1143844.1143874
- Fraud Detection Handbook — metrics: https://fraud-detection-handbook.github.io/fraud-detection-handbook/Chapter_4_PerformanceMetrics/Introduction.html · validation: .../Chapter_5_ModelValidationAndSelection/ValidationStrategies.html

## 7. Explainability
- Deployed TreeSHAP mule pipeline, analyst yield 61% → 89% — https://arxiv.org/abs/2607.17586
- TreeExplainer stability vs DeepExplainer — https://arxiv.org/abs/2604.14231
- EBM glassbox — https://arxiv.org/abs/2602.06955
- XAI human audit / automation-bias risk (3,735 analyst reviews) — https://arxiv.org/abs/2604.22662
- LLM rationales contradict attributions; SHAP/LIME order disagreement — https://arxiv.org/abs/2608.08126
- Plausible rationale ≠ better decision — https://arxiv.org/abs/2607.19266
- Attention is not Explanation — https://arxiv.org/abs/1902.10186 · https://arxiv.org/abs/1906.03731 · rebuttal https://arxiv.org/abs/1908.04626
- US supervisory framing (OCC 2011-12, SR 11-7) — https://arxiv.org/abs/2605.04076

## 8. Adversarial ML / red teaming
- Transferable evasion on card-fraud models — https://arxiv.org/abs/2508.14699
- Financial model degradation under perturbation — https://arxiv.org/abs/2512.15780
- Temporal-graph poisoning — https://arxiv.org/abs/2511.07379
- **TabAttackBench** (attack success vs perturbation realism) — https://arxiv.org/abs/2505.21027
- **TabularBench** (constrained tabular robustness; CAA/CAPGD/MoEvA2) — https://github.com/serval-uni-lu/tabularbench · https://arxiv.org/abs/2408.07579 · https://arxiv.org/abs/2406.00775
- **ART** (MIT; supports scikit-learn/XGBoost/LightGBM) — https://github.com/Trusted-AI/adversarial-robustness-toolbox
- Counterfit — https://github.com/Azure/counterfit · PyRIT (use microsoft/PyRIT) — https://github.com/microsoft/PyRIT · garak — https://github.com/NVIDIA/garak · promptfoo — https://github.com/promptfoo/promptfoo
- Concept drift invisible to label-free monitoring — https://arxiv.org/abs/2604.15740 · https://arxiv.org/abs/2604.17836
- **MITRE ATLAS v5.6.0** (16 tactics, 170 techniques, 57 case studies) — https://raw.githubusercontent.com/mitre-atlas/atlas-data/main/dist/ATLAS.yaml

## 9. LLM security
- OWASP Top 10 for LLM Applications 2025 — https://genai.owasp.org/llm-top-10/
- Multi-step indirect injection (ASR +31.2 pts) — https://arxiv.org/abs/2608.06477
- Automated agent red-teaming, 86.7% ASR on AgentDojo — https://arxiv.org/abs/2608.05108
- Tool/search channel injection (55.9% ASR) — https://arxiv.org/abs/2608.04565
- Agent-skill scanning: only 42% NL-injection detection — https://arxiv.org/abs/2608.08468
- Attacks outpace defenses 3.9:1 — https://arxiv.org/abs/2608.10530
- Capabilities/zero-trust over agent-centric defense — https://arxiv.org/abs/2608.12172
- RAG-grounded fraud reasoning (FP 17.2% → 3.5%) — https://arxiv.org/abs/2601.19684
- RL-trained LLM fraud pilot — https://arxiv.org/abs/2607.23075
- XGBoost ~9× faster than LLM detectors — https://arxiv.org/abs/2605.01143
- LLM-as-judge unreliability — https://arxiv.org/abs/2608.07641 · bias https://arxiv.org/abs/2608.07762 · checklists https://arxiv.org/abs/2608.04783
- Feedzai applied LLM benchmark (smaller beat bigger) — https://medium.com/feedzaitech/benchmarking-llms-in-real-world-applications-pitfalls-and-surprises-78e720d3bfa1

## 10. Production architecture
- Stripe Radar (<100 ms, >1,000 characteristics, 0.1% false block) — https://stripe.dev/blog/how-we-built-it-stripe-radar
- Uber RADAR (generated rules + streaming) — https://www.uber.com/blog/project-radar-intelligent-early-fraud-detection/
- Grab RGCN fraud graph — https://engineering.grab.com/graph-for-fraud-detection
- Feedzai probabilistic thinning (90% write reduction) — https://research.feedzai.com/publication/decoupling-inference-from-state-updates-in-low-latency-feature-engines-via-probabilistic-thinning/
- LLM serving latency for AML (P99 6.4–8.7 s) — https://arxiv.org/abs/2605.11232
- `[UNCERTAIN]` Visa/Mastercard authorization millisecond SLA — **never state as fact**

## 11. Payments standards (for schema fidelity)
- ISO 8583 (DE18 MCC, DE22 POS entry mode, DE39 response code, DE55 EMV TLV) — https://en.wikipedia.org/wiki/ISO_8583
- ISO 20022 message definitions (caaa.001 AcceptorAuthorisationRequest, pacs.008…) — https://www.iso20022.org/iso-20022-message-definitions
- EMV tags (9F02, 9F26 ARQC, 9F36 ATC, 95 TVR…) — https://emvlab.org/emvtags/all/
- 3-D Secure 2 AReq reference (v2.3.1) — https://docs.3dsecure.io/3dsv2/reference.html
- EMVCo payment tokenisation / PAR — https://www.emvco.com/emv-technologies/payment-tokenisation/
- MCC / ISO 18245 — https://en.wikipedia.org/wiki/Merchant_category_code
- AVS response codes — https://en.wikipedia.org/wiki/Address_verification_service

## 12. Datasets (reference only — we generate our own)
Decision: **no external dataset is used.** Recorded for the deck's "why synthetic" argument.
- ULB Credit Card Fraud (284,807 rows, 492 frauds = 0.172%, PCA V1–V28) — https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
- IEEE-CIS (871 cols, 1.35 GB; **real masked transactions, rules-gated — EXCLUDED**) — https://www.kaggle.com/competitions/ieee-fraud-detection/data
- PaySim (6,362,620 rows; simulator **GPL-3.0**) — https://github.com/EdgarLopezPhD/PaySim
- Sparkov generator (**MIT**) — https://github.com/namebrandon/Sparkov_Data_Generation
- IBM TabFormer (24M records, **Apache-2.0**) — https://github.com/IBM/TabFormer
- Feedzai Bank Account Fraud, NeurIPS 2022 (6 × 1M rows, 30 features) — https://github.com/feedzai/bank-account-fraud · https://arxiv.org/abs/2211.13358
- Faker (**MIT**) — https://github.com/joke2k/faker · Mimesis (**MIT**) — https://github.com/lk-geimfari/mimesis
- ⚠️ **SDV / CTGAN are Business Source License — NOT OSI-approved.** Excluded on licence grounds
  (Kaggle Foundational §6c requires OSI licences permitting commercial use).

## 13. Commercial landscape
- Feedzai — https://feedzai.com · adversarial-ML webinar https://www.feedzai.com/resource/the-new-arms-race-fortify-your-ai-against-attacks/ · ECB digital-euro tender + $75M at $2B https://www.finovate.com/feedzai-raises-75-million-partners-with-ecb-to-safeguard-digital-euro/
- Sardine — https://www.sardine.ai · https://www.sardine.ai/agentic-ai-for-fraud · backtesting gap admission https://www.sardine.ai/learn/backtesting
- Sift — https://sift.com · Workflow Simulation https://sift.com/blog/introducing-workflow-simulation/
- Forter — https://www.forter.com/ (down round: $1.3B Mar 2025 vs $3B May 2021)
- `[NOT FOUND]` Independent review-site criticism for all four vendors (G2/Gartner/TrustRadius/PeerSpot all gated)
