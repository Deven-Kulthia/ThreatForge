# Kaggle Writeup — exact field values

Aligned to the host's **Official Submission Guidelines** (posted by `raahul`), which override
the generic competition text where they differ.

**Team:** ThreatForge · **Member:** Deven Kulthia `<devenkulthia007@gmail.com>`
**Public repo:** https://github.com/Deven-Kulthia/ThreatForge
**Deadline:** 31 Aug 2026, 11:59 PM IST

## What the host's guide changed

| Requirement | Source | Consequence |
|---|---|---|
| Repo must be **public** and **named after the team** | Step 4 | Repo renamed `aegis-ai-defence-lab` → **ThreatForge**, visibility flipped to public |
| Upload a **Word document** named `TeamName.docx` | Step 3 | `.pptx` alone is not sufficient → `artifacts/ThreatForge.docx` |
| Project Description must list **team members' full names + registered email IDs** | Step 2 | Added at the top of the description |
| A deployed/hosted URL is **not** mandatory | Host reply to Shreyas | Local run instructions in the repo satisfy the prototype requirement |
| GitHub only — not GitLab/Codeberg | Host reply to Mihir | Already GitHub |

---

## 1 · Title  *(max 80)*

```
Aegis — a closed-loop red team / blue team defence for GenAI payment fraud
```
*74 / 80.*

## 2 · Subtitle  *(max 140)*

```
Generates 25 GenAI-era attacks, trains the defence on them, then grades detection per declared signal so blind spots become the next attack.
```
*140 / 140 — exactly at the limit; do not add a full stop.*

## 3 · Writeup URL  *(max 50)*

```
threatforge-aegis-payment-security
```
*34 / 50.* Change it before submitting, while nothing links to it yet.

## 4 · Submission Track

Auto-selected: **AI Defense Lab for Payment Security**. Already complete.

## 5 · Card and Thumbnail Image  *(560 × 280)*

Upload `artifacts/aegis-card-560x280.png`. Rebuild: `python3 scripts/make_thumbnail.py`.

## 6 · Project Description

**Start with this block** — Step 2 requires team names and registered emails:

```
Team: ThreatForge
Member: Deven Kulthia — devenkulthia007@gmail.com (registered on Luma)
Public repository: https://github.com/Deven-Kulthia/ThreatForge
Solution walkthrough: ThreatForge.docx (attached)
```

Then paste the whole of `docs/submission-writeup.md`, minus the `> **Paste target:**` note at
the top.

## 7 · Project Links  *(Step 4)*

| URL |
|---|
| `https://github.com/Deven-Kulthia/ThreatForge` |

Title:
```
ThreatForge — public source repository
```

Description:
```
Public repository named after the team, per Step 4 of the submission guidelines.
Contains all three pillars (identify, generate, defend), the web prototype, 113
tests, and one-command verification. Run instructions in README.
```

**Do not add Kaggle Datasets / Code / Models / Benchmarks resources** — the repo is public and
the files attach directly, so a Dataset would only duplicate the source.

## 8 · Project Files  *(max 100 MB each)*

| File | Path | Size | Serves |
|---|---|---|---|
| **`ThreatForge.docx`** | `artifacts/ThreatForge.docx` | 45 KB | **Required by Step 3** — solution walkthrough |
| `aegis-walkthrough.pptx` | `artifacts/aegis-walkthrough.pptx` | 758 KB | 15-slide deck (supplementary) |
| `aegis-project-explained.pdf` | `artifacts/aegis-project-explained.pdf` | 302 KB | 31-page technical depth (supplementary) |

`ThreatForge.docx` is the one the guide names. The other two are extra depth, not substitutes.
The source zip is no longer needed as an attachment now that the repo is public — keep it only
if you want a frozen snapshot.

Rebuild the docx:
```bash
.venv/bin/python scripts/make_docx.py --team "ThreatForge" \
  --members "Deven Kulthia <devenkulthia007@gmail.com>" \
  --repo "https://github.com/Deven-Kulthia/ThreatForge"
```

## 9 · Media gallery  *(optional, recommended)*

Upload the 8 captures from `artifacts/screenshots/` — evidences the working prototype without
a judge running anything.

| File | Caption |
|---|---|
| `01-overview.png` | Executive overview — verified metrics, alert bands, the closed loop |
| `02-red-team.png` | Red team — 25 vectors, each declaring its expected detection signals up front |
| `03-campaign-result.png` | Per-signal grading — which declared signals fired, and which missed |
| `04-live-stream.png` | Blue team — scored authorization feed with recommended actions |
| `05-investigate.png` | Exact additive score decomposition, reason codes, counterfactual |
| `06-fraud-network.png` | Shared-infrastructure graph — one device linked to 31 distinct cards |
| `07-performance.png` | Full evaluation — three operating points, calibration, worst-first recall |
| `08-audit-trail.png` | Append-only audit trail for model governance |

No video required; if added later it must be YouTube-hosted.

---

## Final checklist (host's own, Step 5)

- [x] Team formed on Kaggle — solo is permitted (1–5 members)
- [ ] Project Description includes full name + registered email
- [ ] `ThreatForge.docx` uploaded under FILES
- [x] Public GitHub repo named `ThreatForge`
- [ ] Writeup URL slug changed
- [ ] **Submitted** — not left as a draft

> *"Only submissions completed and submitted on Kaggle before the deadline will be judged.
> Drafts or unsubmitted Writeups will not be considered."*

Editing after submitting is allowed until the deadline.
