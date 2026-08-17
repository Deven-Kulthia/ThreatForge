# Competition Brief — Mastercard Innovation Challenge 2026

**Doc status:** ✅ VERIFIED against the official Kaggle competition page. Last updated 2026-08-17.
**Primary source:** Kaggle competition page (participant-supplied HTML, converted to
`research/kaggle-raw/overview.txt`), cross-checked against Luma and the Mastercard AI Garage
LinkedIn announcement.

**Provenance tags:** `[V]` verified from official source · `[U]` participant-supplied ·
`[?]` still unknown · `[A]` our own analysis (never presented as a Mastercard requirement).

---

## 1. Identity `[V]`

| Field | Value |
|---|---|
| Competition | Mastercard Innovation Challenge 2026 |
| Kaggle subtitle | "AI red teaming challenge to identify, simulate, and defend against GenAI-powered payment frauds" |
| Full title | Mastercard Innovation Challenge @ GFF 2026 — AI Defense Lab for Payment Security |
| Tagline | "Build the attack, then build the defense." |
| Kaggle type | **Community Hackathon · Private** |
| Points/medals | "Does not award Points or Medals" |
| Host / judge listed | `raahul` (single host+judge account on Kaggle) |
| Organizer | Mastercard AI Garage |
| GFF 2026 | Jio World Centre, Mumbai. Description says "9–11 September"; timeline table says "8th-11th Sep." Minor inconsistency in Mastercard's own copy `[V]` |

### ⚠️ RESOLVED: human-judged, NOT leaderboard-scored `[V]`

Decisive evidence from the page:
- Submission is a **writeup**: "You haven't created a writeup yet." Artifacts are "submitted from
  the **'Writeups'** section."
- A **Judges** section exists and lists a person.
- "Does not award Points or Medals" — no competitive leaderboard mechanics.
- No scoring metric, no train/test split, no `sample_submission.csv`, no dataset anywhere.

**Consequence:** there is no metric to game. Every point comes from what a human judge reads,
watches, and believes. Narrative quality, demo reliability and UI polish are *first-class
engineering requirements*, not garnish.

## 2. Official challenge statement `[V]`

Verbatim from the Overview:

> GenAI is making payment fraud faster, cheaper, and harder to spot. In this red team/blue team
> challenge, you take on both sides of the problem by building one end-to-end Red Teaming AI
> system that:
> - Identifies novel emerging GenAI-powered payment fraud attacks,
> - Generates realistic simulations of those attacks at scale, and
> - Defends against them with an accurate detection model.

And the stated Goal — **this is the most important sentence in the whole brief:**

> **Goal:** Build a **closed-loop** AI system that discovers emerging GenAI payment fraud,
> recreates it with high fidelity, and reliably detects it. **The best solutions turn their own
> simulated attacks into the training ground for a stronger defense.**

Reinforced in the Description:

> This is a **closed-loop**, red-team/blue-team challenge… The strongest submissions treat these
> three pillars as **a single feedback loop**: the attacks you generate become the training and
> stress-testing ground for the defense you build, and **the gaps your defense reveals feed back
> into new attack ideas.**

> `[A]` **Strategic reading:** Mastercard has told us, twice and explicitly, what a winning
> submission looks like — a *loop*, not a pipeline. Three strong-but-separate modules score worse
> than three modules wired into a cycle where attacks train the defense and defensive gaps
> generate new attacks. This is the single highest-leverage design constraint we have, and most
> entrants will build a linear pipeline instead. **The loop must be visible in the UI, measurable
> in the metrics, and central to the deck.**

## 3. The three pillars — official wording and what each rewards `[V]`

### Pillar 1 — Identify (ideate)
> Research and map the landscape of emerging, novel GenAI-powered fraud attacks targeting
> payments. **Be thorough and exhaustive: the goal is breadth and depth.** Surface as many
> distinct, plausible attack vectors as possible **across channels, rails, and social-engineering
> surfaces** rather than a narrow handful. **Ground each idea in how real payment systems and
> fraud actually work.**

Rewards: **quantity × plausibility.** "As many distinct vectors as possible" is close to a
literal instruction to maximize a count. "Across channels, rails, and social-engineering
surfaces" tells us the axes to spread along. "Ground each idea in how real payment systems
actually work" is the guard against inventing nonsense — payments realism is scored.

### Pillar 2 — Generate
> Build algorithms and **agents** that generate and simulate those attacks **at scale**.
> **Prioritise fidelity:** the synthetic attacks and transactions should closely resemble real
> payment data and real fraud patterns — **realistic distributions, behaviours and edge cases**
> so they are genuinely useful for training and stress-testing a defense.

Rewards: **statistical realism**, explicitly — distributions, behaviours, edge cases. Note the
stated purpose: data "genuinely useful for training and stress-testing a defense." Fidelity is
judged instrumentally, so we should *prove* fidelity, not merely assert it.

### Pillar 3 — Defend
> Build an AI/ML solution (for example, a classifier) that detects, flags, and mitigates the
> generated attacks. **Prioritise accuracy: maximise detection performance (precision, recall,
> F1 / AUC)** on the simulated attacks **while keeping false positives on legitimate payments low.**

Rewards: named metrics — **precision, recall, F1, AUC, and low false positives.** Mastercard
specified the metric vocabulary; our evaluation must report exactly these, honestly measured.

## 4. Official evaluation criteria `[V]`

There are **two official lists**, at different levels of formality. Both are authoritative; they
are not in conflict — the Overview is the emphasized subset, the Rules T&C is the exhaustive set.

### 4.1 The Overview list — 5 emphasized criteria `[V]`

Stated three times on the Overview page (Overview, Tracks and Awards, Evaluation) and
**identical every time**:

| # | Criterion (official wording) | What it actually tests |
|---|---|---|
| 1 | **Diversity of attacks identified** | Breadth × distinctness of the taxonomy |
| 2 | **Fidelity of attacks in simulation** | Do synthetic attacks look like real fraud, statistically |
| 3 | **Detection algorithm efficacy** | Precision / recall / F1 / AUC with low FPs |
| 4 | **Novelty of the overall solution** | System-level originality, not just model choice |
| 5 | **Real-world feasibility in live payments** | Latency, deployability, payments realism |

### 4.2 The Rules T&C list — 14 criteria `[V]`

Rules §8 "Judging and Selection of Winners", verbatim:

> Submissions will be evaluated by a panel designated by Mastercard using criteria that **may
> include** diversity of attacks identified, fidelity of attacks in simulation, detection
> algorithm efficacy, novelty of the solution, real-world feasibility in live payments,
> **innovation, originality, technical quality, relevance to the challenge statement,
> effectiveness, feasibility, scalability, commercial viability and quality of presentation**.

> Mastercard reserves the right to determine the evaluation process, criteria and **weightage in
> its sole discretion**. All decisions … shall be final, binding and not subject to challenge or appeal.

Full enumerated set (14):

| # | Criterion | Also in Overview? |
|---|---|---|
| 1 | Diversity of attacks identified | ✅ |
| 2 | Fidelity of attacks in simulation | ✅ |
| 3 | Detection algorithm efficacy | ✅ |
| 4 | Novelty of the solution | ✅ |
| 5 | Real-world feasibility in live payments | ✅ |
| 6 | Innovation | — |
| 7 | Originality | — |
| 8 | Technical quality | — |
| 9 | **Relevance to the challenge statement** | — |
| 10 | Effectiveness | — |
| 11 | Feasibility | — |
| 12 | Scalability | — |
| 13 | Commercial viability | — |
| 14 | Quality of presentation | — |

### 4.3 ⚠️ Correction — retracting an earlier claim in this document

An earlier revision of this file asserted that scalability, commercial viability and
presentation quality were **not** official criteria, and that the participant's brief was a
superset. **That was wrong.** The participant's list came from Rules §8 and is accurate. All 14
are officially named; only the *emphasis* differs between the Overview and the Rules.

Corrected guidance:
- **Optimize the Overview 5** — they are repeated three times and headline the challenge, so
  they carry the most weight in practice.
- **But cover all 14.** Scalability, commercial viability and presentation quality are named in
  the binding T&C. A deck section on deployment scale and commercial fit is *rubric-aligned*, not
  a distraction — just not at the expense of attack diversity.
- **"Relevance to the challenge statement" (#9) is a free criterion most entrants will overlook.**
  It rewards explicitly mapping our solution back onto Identify / Generate / Defend. Cheap to
  earn: structure the repo, deck and UI around the three pillars by name.
- **Weights are at Mastercard's sole discretion and unpublished** `[?]`. No weighting is
  inferable; assume the Overview 5 dominate and treat the other 9 as tie-breakers.

## 5. Submission requirements `[V]`

> A valid submission (write-up) must contain the following three artifacts, submitted from the
> "Writeups" section prior to the deadline. **Any un-submitted or draft work by the deadline will
> not be considered by the judges.**

| # | Artifact | Official requirement |
|---|---|---|
| 1 | **Code Repository** | "A complete, runnable code repository covering all three pillars — identify, generate, and defend. Your code should be organized, documented and reproducible." |
| 2 | **Solution Walkthrough** | ".pptx / .docx / .pdf" covering: the novel attacks identified · how the system generates/simulates them · the detection & mitigation model **with efficacy results** · real-world feasibility in live payments |
| 3 | **Working Prototype (Web)** | "A working web-based prototype with a presentable UI that demonstrates the **closed-loop system in action**." |

> ⚠️ **Operational risk:** "draft work will not be considered." A finished writeup left in draft
> state = disqualification. **Submit early, then update.** Add to the final audit.

Note the deck's mandated contents map 1:1 onto the five criteria — the walkthrough is where
criteria 1, 3 and 5 are most directly evidenced. And artifact 3 must show the **closed loop**
"in action," which again confirms the loop is the centrepiece.

## 6. Timeline `[V]`

| Milestone | Date |
|---|---|
| Registration opened | 10 Aug 2026 |
| **Registration closes** | **20 Aug 2026** — 3 days from now ⚠️ |
| **Submission deadline** | **31 Aug 2026, 11:59 PM GMT+5:30** (confirmed verbatim on Kaggle) |
| Results announced | 5 Sep 2026 |
| Top teams present at GFF 2026 | 8–11 Sep 2026, Mumbai |

Page showed "14 days to go" as of 2026-08-17 and "Start 7 days ago" (competition opened ~10 Aug).
**Effective build window: 14 days.**

## 7. Eligibility `[V]`

Open to: Startups · Individuals (tech professionals, market researchers, others) ·
Students (UG/PG/doctoral) · Financial Institutions, Fintechs & DeepTech teams.

> "Teams can have **1-5 members**." — solo entry is explicitly permitted. Ours is **solo** `[U]`.

## 8. Prizes `[V]`

| Place | Amount |
|---|---|
| 1st | ₹2,56,000 (~$2,690) |
| 2nd | ₹1,28,000 (~$1,345) |
| 3rd | ₹64,000 (~$672) |
| Track pool | $4,707 |

Plus a showcase opportunity at GFF 2026, Mumbai.

## 9. Competitive intelligence `[V]` — as of 2026-08-17

Straight from the page's participation counters:

| Metric | Value |
|---|---|
| Entrants | **453** |
| Participants | **3** |
| Teams | **3** |
| Submissions | **3** |

`[A]` **Interpretation — cautiously.** 453 people joined the Kaggle page; only 3 have submitted
anything so far, 14 days before the deadline. On Kaggle, "Submissions" on a writeup hackathon
counts created writeups, so this is *early-bird* activity, not final field size. Expect a large
deadline surge, and note the Luma page showed 776 "Going."

Realistic read: the serious field is likely **dozens, not hundreds**, and a genuinely complete
closed-loop submission with a working UI will clear most of it. Do not treat 3 as the field size.

## 10. What remains unknown `[?]`

| # | Unknown | How to resolve | Priority |
|---|---|---|---|
| 1 | Criteria **weights** | Explicitly "sole discretion" of Mastercard — will never be published | Closed; assume Overview 5 dominate |
| 2 | Whether judges **run the code** or only watch the demo | Not stated anywhere | Medium — we mitigate by making setup one-command *and* the demo self-contained |
| 3 | Explicit **LLM-API policy** | Not addressed in either rules layer | Medium — see §12.4 |
| 4 | Presentation format at GFF for finalists | Post-results concern | None now |

Resolved by the Rules tab: external-data/code-sharing/open-source policy, IP terms, data
constraints, eligibility, arbitration. See §12.

## 11. Consequences of the confirmed constraints `[A]`

### 11.1 No dataset is provided — the generator is a scored deliverable

Confirmed: no dataset anywhere on the page. Pillar 2 ("Generate") *is* data creation, and
criterion 2 scores its **fidelity**. So the synthetic generator is not plumbing; it is roughly
20% of the score on its own, and it feeds criteria 1 and 3 as well.

**The trap to avoid:** if fraud is generated by an obviously different process from legitimate
traffic, any classifier scores ~0.99 and the evaluation is meaningless. A payments-literate judge
will spot this immediately, and criterion 2 (fidelity) plus criterion 3 (efficacy) are both
compromised by it. We must deliberately generate **statistically hard** attacks — overlapping
distributions, adaptive evasion, camouflage — and report honest, imperfect numbers. A defensible
F1 beats a suspicious 0.99.

### 11.2 Solo build, 14 days, four deliverables

Dominant failure mode: an ambitious architecture that is 70% done on 31 Aug and demos nothing.
Operating rules:
- **Demo path first** — anything off the judge's path is optional until the path runs end to end.
- **Vertical slices** — one attack type flowing generator → detector → score → explanation → UI
  beats ten half-built modules.
- **Submit the writeup early**, then iterate (draft ≠ submitted).
- Every component must name the criterion it serves, or it gets cut.
- Boring, reliable tech. A broken live demo costs more than any missing feature.

### 11.3 Where the marginal point is cheapest `[A]`

| Criterion | Typical entrant | Our leverage |
|---|---|---|
| Diversity of attacks | 3–6 attack types | **High** — brief says "as many as possible"; a rigorous 20+ vector taxonomy is cheap to produce and directly scored |
| Fidelity | Random noise labelled "fraud" | **High** — payments-credible schema + statistical fidelity evidence |
| Detection efficacy | XGBoost, one number | Medium — table stakes; differentiate via honest, hard evaluation |
| Novelty | "XGBoost + dashboard" | **High** — the closed loop itself, if genuinely implemented |
| Live-payment feasibility | Ignored | **High** — latency budgets, auth-message realism, deployment story |

Cheapest wins: **attack diversity, fidelity evidence, and the closed loop.** Detection modelling
is the most crowded axis and the least differentiating per hour spent.

## 12. Binding rules → engineering constraints `[V]`

Source: Kaggle **Rules** tab = Mastercard's "AI Defence Lab for Payment Security Hackathon"
Terms & Conditions, **plus** Kaggle's Foundational Competition Rules. Note the precedence clause:

> Competition participants must also agree to Kaggle's Foundational Competition Rules. **These
> rules will supersede the competition-specific rules in the event of any conflict.**

### 12.1 Data constraints — now VERIFIED verbatim (Rules §3)

The participant's brief quoted these accurately. Official wording:

> Participants shall: (a) **use only synthetic, anonymized or authorized sample data and not use
> any real cardholder, PII or production payment data**; (b) ensure that all adversarial testing
> **remains within the scope of the Event and does not target live systems, payment infrastructure
> or third parties**; and (c) comply with applicable laws and **responsible AI, cybersecurity and
> security disclosure practices**.

**Engineering consequences (non-negotiable):**
- 100% self-generated synthetic data. No real datasets, no scraped PII, no production data.
- The attack simulator must be **architecturally incapable of reaching an external network
  target** — enforced in code, tested, and documented. Clause (b) makes this a rules requirement,
  not just good practice.
- Every synthetic record and UI surface labelled as synthetic.
- Responsible-AI posture is *named in the rules* → a `docs/security.md` + responsible-AI section
  is compliance evidence, not padding.

### 12.2 Submission mechanics (Rules §2, §3; Overview)

- Submit from the **Writeups** section. **"Any un-submitted or draft work by the deadline will not
  be considered as eligible entry or Submission."**
- **"A valid submission must include all three required artifacts"** — code repo, walkthrough
  (.pptx/.docx/.pdf), working web prototype with presentable UI. Missing one ⇒ invalid.
- **One submission per team** (Rules §1b). No iterating across multiple entries.
- Kaggle Foundational §4d: submissions void if "illegible, incomplete, damaged, altered … or late."

> **Action:** create the writeup and submit a minimum-viable version *days early*, then update it.
> A polished draft left unsubmitted scores zero.

### 12.3 Open-source licensing — a real constraint on dependencies

Kaggle Foundational §6c:

> if open source code is used in the model to generate the Submission, then you must **only use
> open source code licensed under an Open Source Initiative-approved license … that in no event
> limits commercial use** of such code or model containing or depending on such code.

**Engineering consequence:** prefer **MIT / BSD / Apache-2.0** dependencies. Avoid **AGPL** and
treat strong-copyleft as a risk; the "no limit on commercial use" test is safest satisfied by
permissive licences. Practically all of our likely stack (FastAPI, scikit-learn, pandas, React,
Tailwind) is MIT/BSD/Apache-2.0. **We will produce a dependency licence inventory before
submission** — Rules §9b lets Mastercard demand remediation of "license conflicts," so this is a
prize-eligibility issue.

### 12.4 Code sharing (Kaggle Foundational §6a, §6b)

- **No private sharing** of competition code outside the team during the Competition Period.
- Public sharing is permitted **only** on Kaggle forums/notebooks for that competition — and
  doing so **deems the code OSI-licensed** to all competitors.
- `[A]` Consequence: **keep the repo private until after judging.** Publishing to a public GitHub
  repo mid-competition sits in an ambiguous zone between §6a and §6b; a private repo shared with
  judges via the writeup avoids the question entirely. Publish freely after 5 Sep.
- `[A]` On LLM APIs: neither rules layer prohibits calling an external model API. §6c governs
  *open-source code in the model*, not hosted services. **Reasonable inference (not verified):
  LLM APIs are permitted.** We still design so the demo runs without one — a live API is a demo
  reliability risk regardless of permission.

### 12.5 IP — favourable (Rules §5)

> **All intellectual property rights in a Submission shall remain with the participant.** Nothing
> in these Terms transfers ownership … Participants grant Mastercard a non-exclusive,
> royalty-free, irrevocable, perpetual, worldwide right and license to review, evaluate,
> reproduce, display and use the Submission for purposes relating to administration, judging,
> promotion and documentation of the Event.

We keep ownership; Mastercard gets a broad but purpose-limited licence. Rules §6 additionally
requires acknowledging Mastercard may independently develop similar solutions, and waiving
similarity claims. Nothing here blocks commercializing the work later.

### 12.6 Eligibility fine print (Rules §1, Foundational §1)

- 18+; team ≤ 5; **one team per person; one submission per team**; all members registered at
  registration time.
- **Must not be a Mastercard employee/officer/director/contractor/temp staff.**
- One Kaggle account only (Foundational §5a) — multiple accounts ⇒ disqualification.
- Not a resident of Crimea/DNR/LNR, Cuba, Iran, North Korea; not under US sanctions/export controls.
- Submission must be original, non-infringing, and free of third-party confidential information
  (Rules §3, §7; Foundational §14a).

### 12.7 Other

- **Evaluation window 1–4 Sep 2026; results 5 Sep 2026** (Rules §8) — confirms the participant's brief.
- Governing law **India**; disputes by **SIAC arbitration**, single arbitrator, venue **Gurgaon**.
- Winner taxes are the participant's responsibility; withholding applies.
- Publicity: Mastercard may use name/team name/photos for promotion.
- Mastercard may amend timelines, criteria, eligibility or prizes, or cancel, at sole discretion
  ⇒ **re-check the competition page before submitting.**
- `[A]` **Boilerplate tension, resolved:** Foundational §7 describes leaderboard/private-test-set
  scoring, and §18 defines "Competition Data." Neither applies here — there is no dataset and no
  leaderboard, and this is a Community Hackathon judged from writeups by a named judge panel. The
  supersession clause is about *conflicts*, and generic leaderboard machinery is inapplicable
  rather than conflicting. **Judged-submission remains the correct operating model** (high confidence).

### 12.8 ✅ Registration status — apparently complete

The Rules tab shows, for this account:

> ✅ **"You have accepted the rules for this competition. Good luck!"**

On Kaggle, accepting the rules *is* competition entry. So Kaggle-side entry appears **done**.
`[U]` Worth a 30-second confirmation that any separate Luma/Mastercard registration form was also
completed before **20 Aug**, since Rules §1c requires all participants identified at registration.

---

## Sources

| Source | URL | Retrieved | Status |
|---|---|---|---|
| **Kaggle competition page** | https://www.kaggle.com/t/4926910fda5e404aa49abd61fee21913 | 2026-08-17 | ✅ **Authoritative** — participant-supplied HTML → `kaggle-raw/overview.txt` |
| Luma event page | https://luma.com/kyz978xv | 2026-08-17 | ✅ Public, consistent with Kaggle |
| LinkedIn announcement | https://www.linkedin.com/posts/mastercard-ai-garage_mastercard-gff2026-globalfintechfest-activity-7493274878331101184-vLJM | 2026-08-17 | ✅ Public; names 4 priority threats |
| **Kaggle Rules tab** | same page, Rules tab | 2026-08-17 | ✅ **Authoritative** — participant-supplied HTML → `kaggle-raw/rules.txt`. Contains Mastercard T&C + Privacy Notice + Kaggle Foundational Rules |
| GFF 2026 | https://www.globalfintechfest.com/ | — | Not fetched; low priority |

### Cross-source consistency check `[V]`

All three sources agree on: dates, prizes, three pillars, three artifacts, red-team/blue-team
framing. No contradictions except the GFF date range (8–11 vs 9–11 Sep) within Mastercard's own
copy. Mastercard's four named priority threats (LinkedIn) — "synthetic identities, deepfake KYC,
fake merchant storefronts and AI-enabled scams" — do not appear on the Kaggle page, but remain a
useful steer for taxonomy coverage.
