# Kaggle Writeup — exact field values

The Kaggle form gates **Submit** behind a 6-item checklist. This file holds the exact
copy-paste value for each item, so nothing is composed under deadline pressure.

**Form URL:** competition page → **Writeups** → your draft
**Deadline:** 31 Aug 2026, 11:59 PM GMT+5:30
**Track:** AI Defense Lab for Payment Security *(single track, auto-selected — already ✅)*

---

## 1 · Title  *(required to save · max 80 chars)*

```
Aegis — a closed-loop red team / blue team defence for GenAI payment fraud
```
*74 / 80 characters.*

## 2 · Subtitle  *(max 140 chars — "explain your project in one sentence")*

```
Generates 25 GenAI-era attacks, trains the defence on them, then grades detection per declared signal so blind spots become the next attack.
```
*140 / 140 characters — exactly at the limit; do not add a full stop or it will truncate.*

## 3 · Writeup URL  *(max 50 chars)*

Kaggle auto-generates a throwaway slug like `new-writeup-1787224712907`. Judges see this
in the address bar, so replace it with:

```
aegis-ai-defence-lab-payment-security
```
*37 / 50 characters.* Final URL becomes
`kaggle.com/competitions/mastercard-innovation-challenge-2026/writeups/aegis-ai-defence-lab-payment-security`

**Do this before submitting.** Kaggle warns "changing the url will break existing links" —
harmless now while nothing points at it, costly once shared.

## 4 · Submission Track

Already complete. Single track, auto-selected: **AI Defense Lab for Payment Security**.

## 5 · Card and Thumbnail Image  *(560 × 280)*

Upload `artifacts/aegis-card-560x280.png` (rendered at 2× for a crisp result).
Rebuild with `python3 scripts/make_thumbnail.py`.

## 6 · Project Description

Paste the **entire contents** of `docs/submission-writeup.md`, with two edits:

1. **Delete** the block at the top beginning `> **Paste target:**` — that is a note to
   ourselves, not to judges.
2. **Delete** the "The three required artifacts" table — the Attachments section below
   now carries those, so the table is redundant and its "where" column points at local
   paths a judge cannot open.

Everything else goes in as-is. It is ~2,500 words, structured on the three pillars, and
covers all 14 official criteria.

## 7 · Project Links

| Label | URL |
|---|---|
| Code repository (private — access on request) | `https://github.com/Deven-Kulthia/aegis-ai-defence-lab` |

Link title (keep it short — Kaggle truncates):

```
Aegis — source repository (private during judging)
```

Description (249 / 255 chars — cites the specific rule and points judges at the code):

```
Private during the competition period per Kaggle Foundational Rules §6a, which
restrict sharing competition code. Full source — including complete commit
history as GIT-HISTORY.txt — is attached as aegis-submission.zip. Read access
available to judges on request.
```

**Do not add Kaggle Datasets / Code / Models / Benchmarks resources.** The files attach
directly (well under the 100 MB limit), so a Dataset would be a second copy of the same
code and only creates ambiguity about which is authoritative.

## 8 · Project Files  *(max 100 MB per upload)*

All three fit comfortably — no Kaggle Dataset needed.

| File | Path | Size | Serves |
|---|---|---|---|
| `aegis-submission.zip` | `artifacts/aegis-submission.zip` | 3.1 MB | **Artifact 1** — code repository (incl. GIT-HISTORY.txt) |
| `aegis-walkthrough.pptx` | `artifacts/aegis-walkthrough.pptx` | 758 KB | **Artifact 2** — solution walkthrough |
| `aegis-project-explained.pdf` | `artifacts/aegis-project-explained.pdf` | 302 KB | Artifact 2 — full technical depth |

Rebuild the zip before uploading: `./scripts/make_submission_zip.sh`
(it is gitignored, and the script aborts if a credential would ship).

## 9 · Media gallery

Upload all 8 captures from `artifacts/screenshots/` — this evidences **Artifact 3**
(working web prototype) even if no judge runs the code. Suggested order and captions:

| File | Caption |
|---|---|
| `01-overview.png` | Executive overview — verified metrics, alert bands, the closed loop |
| `02-red-team.png` | Red team — 25 attack vectors, each declaring its expected detection signals up front |
| `03-campaign-result.png` | Per-signal grading — which declared signals fired, and which were missed |
| `04-live-stream.png` | Blue team — scored authorization feed with recommended actions |
| `05-investigate.png` | Exact additive score decomposition, reason codes and counterfactual |
| `06-fraud-network.png` | Shared-infrastructure graph — one device linked to 31 distinct cards |
| `07-performance.png` | Full evaluation — three operating points, calibration, per-attack recall worst-first |
| `08-audit-trail.png` | Append-only audit trail for model governance |

No video is required. If one is added later it must be hosted on YouTube.

---

## Before clicking Submit

- [ ] All 6 checklist items show complete (Submit stays disabled until then)
- [ ] **Writeup URL changed** off the auto-generated `new-writeup-…` slug
- [ ] Title and subtitle within limits
- [ ] Description pasted, "Paste target" note and artifacts table removed
- [ ] 3 files uploaded, repo link added with the privacy note
- [ ] 8 screenshots in the media gallery
- [ ] Thumbnail uploaded

## Then

**Click `Submit`, not `Save Draft`.** Reload the page afterwards and confirm it does not
say *Draft*.

> Rules §2: *"Any un-submitted or draft work by the deadline will not be considered by
> the judges."*

Editing after submitting is fine — submitted-then-improved counts; drafted-then-forgotten
scores zero.
