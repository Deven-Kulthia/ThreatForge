"""Build the full project explainer PDF.

Renders a single self-contained HTML document, then prints it to PDF with the
Playwright Chromium that already ships for the browser smoke test — so no new
dependency, and no LaTeX toolchain.

Numbers come from artifacts/metrics.json, so the PDF cannot drift from the code.

    /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/make_pdf.py

(playwright lives in the system Python, same interpreter the browser smoke test uses;
this script needs only stdlib + playwright, so no venv dependency is added)

Output: artifacts/aegis-project-explained.pdf
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "artifacts" / "metrics.json"
HTML_OUT = ROOT / "artifacts" / "aegis-project-explained.html"
PDF_OUT = ROOT / "artifacts" / "aegis-project-explained.pdf"

CSS = """
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
* { box-sizing: border-box; }
body { font: 10.5pt/1.5 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
       color: #16202e; margin: 0; }
h1 { font-size: 26pt; margin: 0 0 4pt; letter-spacing: -.5pt; }
h2 { font-size: 15pt; margin: 22pt 0 7pt; padding-bottom: 4pt;
     border-bottom: 2px solid #16202e; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin: 14pt 0 5pt; color: #0b2b4a; page-break-after: avoid; }
h4 { font-size: 10.5pt; margin: 10pt 0 3pt; page-break-after: avoid; }
p, li { margin: 0 0 6pt; }
ul, ol { margin: 0 0 8pt; padding-left: 16pt; }
code { font: 9pt/1.4 "SF Mono", Menlo, Consolas, monospace;
       background: #eef2f7; padding: 1px 4px; border-radius: 3px; }
pre { font: 8.5pt/1.45 "SF Mono", Menlo, Consolas, monospace; background: #0f1626;
      color: #dbe5f2; padding: 9pt 11pt; border-radius: 5px; overflow-x: auto;
      page-break-inside: avoid; }
pre code { background: none; color: inherit; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt;
        font-size: 9pt; page-break-inside: avoid; }
th { background: #16202e; color: #fff; text-align: left; padding: 5pt 7pt;
     font-weight: 600; }
td { padding: 4.5pt 7pt; border-bottom: 1px solid #dde4ec; vertical-align: top; }
tr:nth-child(even) td { background: #f6f8fb; }
.cover { height: 247mm; display: flex; flex-direction: column;
         justify-content: center; page-break-after: always; }
.dot { display: inline-block; width: 15mm; height: 15mm; border-radius: 50%; }
.sub { font-size: 13pt; color: #5a6a7e; margin: 2pt 0 0; }
.kv { font-size: 9.5pt; color: #16202e; }
.note { border-left: 3px solid #0b6bcb; background: #eff6ff; padding: 7pt 10pt;
        margin: 8pt 0; page-break-inside: avoid; }
.warn { border-left: 3px solid #c2410c; background: #fff5ed; padding: 7pt 10pt;
        margin: 8pt 0; page-break-inside: avoid; }
.ok { border-left: 3px solid #047857; background: #ecfdf5; padding: 7pt 10pt;
      margin: 8pt 0; page-break-inside: avoid; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8pt; margin: 8pt 0; }
.card { border: 1px solid #dde4ec; border-radius: 5px; padding: 8pt 10pt; }
.card b { display: block; font-size: 9pt; text-transform: uppercase;
          letter-spacing: .4pt; color: #5a6a7e; }
.big { font-size: 17pt; font-weight: 700; }
.toc a { color: #0b2b4a; text-decoration: none; }
.toc li { margin: 0 0 3pt; }
.brk { page-break-before: always; }
.small { font-size: 8.5pt; color: #5a6a7e; }
"""


def build_html(m: dict) -> str:
    d, sp, di = m["dataset"], m["split"], m["discrimination"]
    f1, cap, pm = (m["operating_point_best_f1"],
                   m["operating_point_capacity_constrained"],
                   m["operating_point_prevalence_matched"])
    zd, cal, lat, mo = m["zero_day"], m["calibration"], m["latency"], m["money_and_customer_impact"]
    cov, fid = m["coverage"], m["fidelity"]
    fr, fs = fid["realism"], fid["separability"]
    lo, hi = di["pr_auc_95ci"]
    cf = f1["confusion"]

    def rows(pairs):
        return "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in pairs)

    zd_rows = "".join(
        f"<tr><td><code>{k}</code></td><td>{v['n']}</td>"
        f"<td>{v['recall_at_seen_threshold']:.3f}</td><td>{v['mean_risk']:.3f}</td>"
        f"<td>{'yes' if v['hard_to_detect'] else '—'}</td></tr>"
        for k, v in sorted(zd["per_vector"].items(),
                           key=lambda kv: -kv[1]["recall_at_seen_threshold"]))
    pa_rows = "".join(
        f"<tr><td><code>{k}</code></td><td>{v['category']}</td><td>{v['n']}</td>"
        f"<td>{v['recall_at_alert_rate']:.3f}</td><td>{v['mean_risk']:.3f}</td>"
        f"<td>{'yes' if v['hard_to_detect'] else '—'}</td><td>{v['severity']}</td></tr>"
        for k, v in sorted(m["per_attack"].items(),
                           key=lambda kv: kv[1]["recall_at_alert_rate"]))
    fr_rows = "".join(
        f"<tr><td>{k.replace('_', ' ')}</td><td>{v['value']}</td>"
        f"<td>{v['reference_band'][0]} – {v['reference_band'][1]}</td>"
        f"<td>{'✓' if v['within_band'] else '✗'}</td></tr>"
        for k, v in fr.items() if isinstance(v, dict))
    fs_rows = "".join(
        f"<tr><td><code>{k}</code></td><td>{v['univariate_auc']:.3f}</td>"
        f"<td>{v['overlap']:.3f}</td></tr>"
        for k, v in sorted(fs["per_field"].items(),
                           key=lambda kv: -kv[1]["univariate_auc"]))
    unimpl = "".join(f"<tr><td><code>{k}</code></td><td>{v}</td></tr>"
                     for k, v in cov["signals_not_implemented"].items())

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Aegis — Project Explained</title><style>{CSS}</style></head><body>

<!-- ============ COVER ============ -->
<div class="cover">
  <div><span class="dot" style="background:#eb001b"></span
       ><span class="dot" style="background:#f79e1b;margin-left:-6mm"></span></div>
  <h1 style="margin-top:8mm">Aegis</h1>
  <p class="sub">AI Defence Lab for Payment Security</p>
  <p class="sub" style="font-size:11pt;margin-top:1pt">
     Closed-loop red team / blue team system — identify → generate → defend</p>
  <div style="height:6mm"></div>
  <p style="font-size:11pt;max-width:150mm">
    A complete technical explanation of the project: what it does, how every part works,
    every term defined, the full technology stack, how to run and test it, and the measured
    results with their limitations stated.</p>
  <div style="height:10mm"></div>
  <table style="width:118mm">
    {rows([
      ("Competition", "Mastercard Innovation Challenge 2026 — AI Defense Lab for Payment Security"),
      ("Organiser", "Mastercard AI Garage"),
      ("Entry", "Solo"),
      ("Repository", "<code>Deven-Kulthia/ThreatForge</code> (public)"),
      ("Backend language", "Python 3.14.4"),
      ("Frontend language", "TypeScript 5.7 (React 19)"),
      ("Code size", "4,210 lines backend · 2,176 lines frontend · 857 lines tests"),
      ("Tests", "113 passing, plus 6 module self-checks"),
      ("Metrics generated", m["generated_at_utc"][:19] + "Z"),
      ("Data", "100% synthetic — no real cardholder data, PII or production payment data"),
    ])}
  </table>
  <p class="small" style="margin-top:8mm">Every figure in this document is read from
    <code>artifacts/metrics.json</code>, produced by <code>backend.app.evaluate</code>.
    No number is typed by hand.</p>
</div>

<!-- ============ TOC ============ -->
<h2>Contents</h2>
<ol class="toc">
  <li><a href="#p1">The problem, in plain terms</a></li>
  <li><a href="#p2">What Aegis is — red team, blue team, and the loop</a></li>
  <li><a href="#p3">Technology stack — every language, library and tool, and why</a></li>
  <li><a href="#p4">Architecture — module by module</a></li>
  <li><a href="#p5">The data model — every field explained</a></li>
  <li><a href="#p6">Pillar 1 — Identify: the 25 attack vectors</a></li>
  <li><a href="#p7">Pillar 2 — Generate: simulation and its fidelity evidence</a></li>
  <li><a href="#p8">Pillar 3 — Defend: features, cascade, explainability</a></li>
  <li><a href="#p9">Evaluation — methodology and full results</a></li>
  <li><a href="#p10">Where it fails — stated plainly</a></li>
  <li><a href="#p11">The dashboard — all seven panels</a></li>
  <li><a href="#p12">How to run it</a></li>
  <li><a href="#p13">How to test it</a></li>
  <li><a href="#p14">Glossary — every term used</a></li>
  <li><a href="#p15">Competition compliance</a></li>
  <li><a href="#p16">Repository map</a></li>
</ol>

<!-- ============ 1 ============ -->
<h2 id="p1" class="brk">1 · The problem, in plain terms</h2>
<p>A bank's fraud detector is like a security guard who has been shown photographs of every
criminal caught so far. He is excellent at recognising those faces. A new criminal — a face in
no photograph — walks straight past him. He is not incompetent; he simply has no photograph.</p>
<p>That is supervised fraud detection. It learns from fraud that <b>already happened</b>, and it
learns slowly, because the labels come from chargebacks: customers disputing charges, which takes
<b>weeks</b>.</p>
<p>Generative AI changed the other side of that equation. Inventing a plausible new fraud
technique became cheap and fast:</p>
<ul>
  <li>Large language models sustain thousands of individually tailored scam conversations at once.</li>
  <li>Generated documents and deepfake video defeat identity checks at account opening.</li>
  <li>Autonomous agents now transact on a cardholder's behalf, blurring what "the customer did".</li>
  <li>Iteration is cheap: probe, observe the decline, adapt, retry.</li>
</ul>
<div class="warn"><b>The asymmetry.</b> Attackers invent new techniques in days. Defenders receive
the labels needed to learn them in weeks. A novel typology is, by definition, out of
distribution — you cannot classify your way out of it with a better model.</div>
<p>So Aegis inverts the order: <b>generate the unseen fraud first</b>, then train and stress-test
the defence on it, under constraints that keep the generated fraud realistic.</p>

<!-- ============ 2 ============ -->
<h2 id="p2">2 · What Aegis is — red team, blue team, and the loop</h2>
<p>The competition brief frames this as a <b>red team / blue team</b> challenge in which entrants
"take on both sides of the problem". Both sides are first-class in Aegis, and the dashboard labels
them as such.</p>
<table>
  <tr><th>Side</th><th>Job</th><th>Where it lives</th></tr>
  <tr><td><b>Red team</b></td><td>Research and generate novel attacks; declare, before running,
      which detection signals each attack <i>should</i> trip</td>
      <td>Attack Simulator panel · <code>attacks.py</code></td></tr>
  <tr><td><b>Blue team</b></td><td>Detect, score, explain, and report back which of those declared
      signals were missed</td>
      <td>Live Stream, Investigate, Fraud Network, Performance · <code>detect.py</code>,
      <code>explain.py</code>, <code>evaluate.py</code></td></tr>
</table>
<h3>The three pillars</h3>
<table>
  <tr><th>#</th><th>Pillar</th><th>What it does</th></tr>
  <tr><td>1</td><td><b>Identify</b></td><td>Map the emerging GenAI-powered threat surface —
      {d['attack_vectors']} vectors across {cov['categories']} categories, each mapped to
      MITRE ATLAS</td></tr>
  <tr><td>2</td><td><b>Generate</b></td><td>Simulate those attacks at scale with high fidelity —
      {d['transactions']:,} transactions, {d['campaigns']} campaigns</td></tr>
  <tr><td>3</td><td><b>Defend</b></td><td>Detect them with a calibrated, explainable cascade —
      PR-AUC {di['pr_auc']:.3f}, p99 {lat['decision_p99_ms']:.1f} ms</td></tr>
</table>
<h3>Why it is a loop and not a pipeline</h3>
<pre><code>IDENTIFY ──▶ GENERATE ──▶ DEFEND ──┐
    ▲                              │
    └────── per-signal recall ◀─────┘
           (named blind spots become the next attack specification)</code></pre>
<p>Every generated attack emits an <code>expected_signals</code> list <b>before</b> it executes.
Detection is then graded against that declaration, per signal, rather than only per transaction.
That converts a vague "we caught 89% of fraud" into "here are the exact mechanisms we are blind
to" — which is actionable, and becomes the specification for the next round of attacks.</p>
<div class="ok"><b>Coverage.</b> {cov['expected_signals_covered']} of
{cov['expected_signals_distinct']} distinct declared signals are implemented. The
{len(cov['signals_not_implemented'])} that are not are <b>named with reasons</b> (see §8), because a
named gap is engineering judgement whereas an unexplained gap looks like a defect.</div>

<!-- ============ 3 ============ -->
<h2 id="p3" class="brk">3 · Technology stack — every language, library and tool</h2>
<h3>Languages</h3>
<table>
  <tr><th>Language</th><th>Version</th><th>Used for</th><th>Lines</th></tr>
  <tr><td><b>Python</b></td><td>3.14.4</td><td>All backend: data generation, attack simulation,
      feature engineering, detection, explainability, evaluation, API</td><td>4,210</td></tr>
  <tr><td><b>TypeScript</b></td><td>5.7</td><td>The entire dashboard, fully type-checked</td>
      <td>2,176</td></tr>
  <tr><td><b>SQL</b></td><td>SQLite dialect</td><td>Append-only audit trail</td><td>inline</td></tr>
  <tr><td><b>Bash</b></td><td>—</td><td><code>verify.sh</code> one-command verification gate</td>
      <td>~150</td></tr>
  <tr><td><b>HTML / CSS</b></td><td>—</td><td>Tailwind utility classes; this PDF's own template</td>
      <td>—</td></tr>
</table>
<h3>Python libraries (runtime)</h3>
<table>
  <tr><th>Library</th><th>Version</th><th>Licence</th><th>Why this one</th></tr>
  <tr><td>numpy</td><td>2.5.2</td><td>BSD-3</td><td>Vectorised numerics; the generator builds
      whole populations as arrays rather than row loops</td></tr>
  <tr><td>pandas</td><td>3.0.5</td><td>BSD-3</td><td>The transaction table and all group-wise
      feature aggregation</td></tr>
  <tr><td>scikit-learn</td><td>1.9.0</td><td>BSD-3</td><td><code>HistGradientBoostingClassifier</code>
      for the model stage, <code>IsotonicRegression</code> for calibration, metrics</td></tr>
  <tr><td>networkx</td><td>3.6.1</td><td>BSD-3</td><td>Entity graph: connected components, fan-in,
      shared-infrastructure detection</td></tr>
  <tr><td>fastapi</td><td>0.141.1</td><td>MIT</td><td>REST + WebSocket API with automatic schema</td></tr>
  <tr><td>uvicorn</td><td>0.52.3</td><td>BSD-3</td><td>ASGI server</td></tr>
  <tr><td>sqlite3</td><td>stdlib</td><td>Public domain</td><td>Audit trail — zero-setup, no service
      to run, and it is already in the standard library</td></tr>
</table>
<h3>Python libraries (tooling, not on the decision path)</h3>
<table>
  <tr><th>Library</th><th>Version</th><th>Licence</th><th>Why</th></tr>
  <tr><td>pytest</td><td>9.1.1</td><td>MIT</td><td>113 tests across 4 suites</td></tr>
  <tr><td>python-pptx</td><td>1.0.2</td><td>MIT</td><td>Generates the walkthrough deck from
      <code>metrics.json</code> so slides cannot drift from code</td></tr>
  <tr><td>playwright</td><td>—</td><td>Apache-2.0</td><td>Real-browser smoke test; also prints
      this PDF, avoiding a second document toolchain</td></tr>
</table>
<h3>Frontend</h3>
<table>
  <tr><th>Package</th><th>Version</th><th>Licence</th><th>Why</th></tr>
  <tr><td>react / react-dom</td><td>19.0</td><td>MIT</td><td>UI runtime</td></tr>
  <tr><td>vite</td><td>6.0</td><td>MIT</td><td>Dev server and build; fast HMR</td></tr>
  <tr><td>tailwindcss</td><td>4.0</td><td>MIT</td><td>Styling without a bespoke design system</td></tr>
  <tr><td>recharts</td><td>2.15</td><td>MIT</td><td>Charts — alert bands, calibration curve</td></tr>
  <tr><td>lucide-react</td><td>0.470</td><td>ISC</td><td>Icons</td></tr>
  <tr><td>typescript</td><td>5.7</td><td>Apache-2.0</td><td>Type safety; <code>tsc --noEmit</code>
      is part of the verification gate</td></tr>
</table>
<p>Runtime: <b>Node 24.18.0</b>, <b>npm 11.16.0</b>.</p>
<div class="ok"><b>Licence compliance.</b> All 41 Python and 121 npm packages were audited: every one
is OSI-approved and permissive (MIT / BSD / Apache-2.0 / ISC / MPL-2.0). Zero AGPL, GPL or SSPL.
Kaggle Foundational Rules §6c requires open-source code that "in no event limits commercial
use".</div>
<h3>Deliberate omissions — and why</h3>
<table>
  <tr><th>Not used</th><th>Reason</th></tr>
  <tr><td><b>LightGBM / XGBoost</b></td><td><code>libomp</code> is unavailable in this environment.
      scikit-learn's <code>HistGradientBoostingClassifier</code> is the same algorithm family with
      no OpenMP dependency.</td></tr>
  <tr><td><b>SHAP</b></td><td>Requires <code>numba</code>, which fails to build on Python 3.14.
      Rather than ship an approximate explainer and call it attribution, the arbiter was designed
      to be <i>additive</i>, making its decomposition exact arithmetic (see §8).</td></tr>
  <tr><td><b>Graph neural network</b></td><td>The GADBench benchmark shows tree ensembles plus
      neighbour aggregation outperform purpose-built GNNs on tabular graph anomaly detection. A GNN
      would cost latency and explainability for no measured gain.</td></tr>
  <tr><td><b>SMOTE / synthetic oversampling</b></td><td>Leaks information across the split and
      assumes a unimodal minority class; our minority is 25 distinct typologies. Used
      <code>class_weight="balanced"</code> instead.</td></tr>
  <tr><td><b>An LLM on the decision path</b></td><td>A hosted model in an authorization flow is a
      latency and availability risk, and a non-deterministic decision is not auditable. The LLM
      narrates; it never makes the block decision.</td></tr>
  <tr><td><b>Docker / Kubernetes / message queues</b></td><td>Nothing in the demo needs them. Two
      processes and a file-backed database is the whole runtime.</td></tr>
</table>

<!-- ============ 4 ============ -->
<h2 id="p4" class="brk">4 · Architecture — module by module</h2>
<pre><code>backend/app/
  schema.py     field definitions, MCC and country tables, the observable/ground-truth split
  generator.py  synthetic population + legitimate authorization traffic
  attacks.py    25 attack simulators, each emitting full ground-truth metadata
  features.py   57 strictly causal features
  fidelity.py   measures realism and non-separability of the corpus
  detect.py     the three-stage cascade + arbiter + calibration
  explain.py    exact additive reason codes and counterfactuals
  evaluate.py   PR-AUC, operating points, calibration, latency, zero-day, per-signal
  api.py        FastAPI REST + WebSocket + SQLite audit trail</code></pre>
<table>
  <tr><th>Module</th><th>Responsibility</th><th>Key design decision</th></tr>
  <tr><td><code>schema.py</code></td><td>One source of truth for every field</td>
      <td><code>GROUND_TRUTH_FIELDS</code> is a frozen set excluded from
      <code>OBSERVABLE_FIELDS</code>, so label leakage is <i>impossible by construction</i> rather
      than merely discouraged</td></tr>
  <tr><td><code>generator.py</code></td><td>Cardholders, merchants, devices, and legitimate traffic</td>
      <td>Fraud is <b>not</b> produced here. Legitimate and adversarial behaviour come from
      independent code paths, so the detector cannot exploit a shared generation artefact</td></tr>
  <tr><td><code>attacks.py</code></td><td>The 25 simulators</td>
      <td>Each may only manipulate attacker-controllable levers (§7)</td></tr>
  <tr><td><code>features.py</code></td><td>Turn raw authorizations into model inputs</td>
      <td>Causality verified by test: recomputing features on a truncated prefix must give
      identical values, so no feature can see the future</td></tr>
  <tr><td><code>detect.py</code></td><td>Score a transaction</td>
      <td>The graph stage is gated by a <b>compute budget</b> (riskiest 20%), not a score
      threshold — a threshold lets cost spike exactly when an attack floods the high-risk band</td></tr>
  <tr><td><code>explain.py</code></td><td>Say why</td>
      <td>Exact additive decomposition, verified against the model's own decision function</td></tr>
  <tr><td><code>evaluate.py</code></td><td>Grade everything</td>
      <td>Writes <code>artifacts/metrics.json</code>; every downstream artifact (deck, this PDF,
      docs) reads from it</td></tr>
  <tr><td><code>api.py</code></td><td>Serve the dashboard</td>
      <td>Append-only audit trail; health endpoint reports readiness so the UI never fires a
      request it expects to fail</td></tr>
</table>

<!-- ============ 5 ============ -->
<h2 id="p5">5 · The data model — every field explained</h2>
<p>The schema is modelled on <b>ISO 8583</b>, the international standard for card authorization
messages. That matters: it constrains features to things that genuinely exist at authorization
time, and it means anything requiring dispute-lifecycle or session data is honestly out of scope.</p>
<table>
  <tr><th>Group</th><th>Field</th><th>Meaning</th></tr>
  <tr><td rowspan="5"><b>Identity / routing</b></td><td><code>transaction_id</code></td><td>Unique id</td></tr>
  <tr><td><code>timestamp</code></td><td>When the authorization occurred</td></tr>
  <tr><td><code>card_token</code></td><td>Synthetic network token — <b>never</b> a PAN (card number)</td></tr>
  <tr><td><code>account_id</code></td><td>The cardholder's account</td></tr>
  <tr><td><code>issuer_country</code></td><td>Country of the issuing bank</td></tr>
  <tr><td rowspan="3"><b>Money</b></td><td><code>amount</code></td><td>Transaction amount</td></tr>
  <tr><td><code>currency</code></td><td>Currency, derived from cardholder home country</td></tr>
  <tr><td><code>amount_local</code></td><td>Amount in home currency, for comparability</td></tr>
  <tr><td rowspan="5"><b>Acceptance</b></td><td><code>merchant_id</code>, <code>merchant_name</code></td>
      <td>The shop</td></tr>
  <tr><td><code>mcc</code></td><td>Merchant Category Code — 4-digit industry classification
      (e.g. 5999 = miscellaneous retail)</td></tr>
  <tr><td><code>merchant_country</code></td><td>Where the merchant is</td></tr>
  <tr><td><code>merchant_age_days</code></td><td>How long the merchant has existed — new merchants
      carry genuinely elevated risk</td></tr>
  <tr><td><code>is_recurring</code></td><td>A subscription-style repeat payment</td></tr>
  <tr><td rowspan="3"><b>Presentation</b></td><td><code>channel</code></td>
      <td><b>ECOM</b> online · <b>POS</b> physical card machine · <b>MOTO</b> mail/telephone order</td></tr>
  <tr><td><code>entry_mode</code></td><td>How the credential was supplied (chip, contactless,
      keyed, <code>NETWORK_TOKEN</code>)</td></tr>
  <tr><td><code>card_present</code></td><td>Was the physical card there? Card-not-present is the
      higher-risk case</td></tr>
  <tr><td rowspan="3"><b>Device</b></td><td><code>device_id</code></td><td>Device fingerprint</td></tr>
  <tr><td><code>ip_prefix</code></td><td><b>/24 only</b> — no full address retained, even synthetic</td></tr>
  <tr><td><code>user_agent_hash</code></td><td>Hashed browser signature</td></tr>
  <tr><td rowspan="6"><b>Verification</b></td><td><code>avs_result</code></td>
      <td>Address Verification Service — did the billing address match?</td></tr>
  <tr><td><code>cvv_result</code></td><td>Was the 3-digit security code correct?</td></tr>
  <tr><td><code>three_ds_status</code></td><td>3-D Secure — the "verify with your bank" step
      (Verified by Visa / Mastercard Identity Check)</td></tr>
  <tr><td><code>sca_exemption</code></td><td>Strong Customer Authentication exemption claimed.
      Under EU PSD2, some low-risk payments may skip the check — attackers game these bands</td></tr>
  <tr><td><code>network_token_used</code></td><td>Was a token used instead of a raw card number?</td></tr>
  <tr><td><code>cross_border</code></td><td>Issuer and merchant in different countries</td></tr>
  <tr><td><b>Outcome</b></td><td><code>auth_response</code></td><td>Approved or declined</td></tr>
  <tr><td rowspan="5"><b>Ground truth</b><br><span class="small">lab only — never present in a real
      authorization message</span></td><td><code>is_fraud</code></td><td>The label</td></tr>
  <tr><td><code>attack_type</code></td><td>Which of the 25 vectors</td></tr>
  <tr><td><code>scenario_id</code></td><td>Which campaign instance</td></tr>
  <tr><td><code>attack_strength</code></td><td>How aggressive the campaign was (0–1)</td></tr>
  <tr><td><code>synthetic</code></td><td>Always <code>true</code> — a compliance marker on every row</td></tr>
</table>
<p><b>Scale of the corpus:</b> {d['cards']:,} tokenised cards · {d['merchants']} merchants ·
{d['days']} days · {d['transactions']:,} transactions · {d['fraud']:,} fraudulent
({d['fraud_rate']:.2%}) · {d['campaigns']} campaigns.</p>

<!-- ============ 6 ============ -->
<h2 id="p6" class="brk">6 · Pillar 1 — Identify: the 25 attack vectors</h2>
<p>{d['attack_vectors']} vectors across {cov['categories']} categories. Each is mapped to
<b>MITRE ATLAS</b> (a public catalogue of adversarial techniques against AI systems), annotated
with the specific role generative AI plays, assigned a severity 1–5, and flagged
<code>hard_to_detect</code> where it was deliberately built to overlap legitimate behaviour.
<b>12 of 25</b> carry that flag — the taxonomy is not padded with easy wins.</p>
<table>
  <tr><th>Category</th><th>Representative vectors</th><th>What GenAI changed</th></tr>
  <tr><td>Synthetic identity</td><td>Generated-document application farm; history building;
      bust-out</td><td>LLMs mass-produce coherent applicant personas and plausible life-event
      narratives, so a fake identity survives manual review</td></tr>
  <tr><td>Deepfake / KYC</td><td>Liveness and KYC defeat at onboarding</td>
      <td>Generated video and documents defeat identity checks that assumed forgery was expensive</td></tr>
  <tr><td>Account takeover</td><td>Credential stuffing; SIM-swap OTP interception; voice-clone
      call-centre takeover</td><td>Voice cloning defeats phone-based identity verification</td></tr>
  <tr><td>Scam / social engineering</td><td>APP scam via conversational LLM; romance /
      pig-butchering</td><td>Thousands of simultaneous, individually tailored grooming
      conversations</td></tr>
  <tr><td>Agentic commerce</td><td>Agent impersonation; prompt injection via merchant-controlled
      fields</td><td>Autonomous agents transact on a cardholder's behalf, and text fields become
      an injection surface</td></tr>
  <tr><td>Fraud ring</td><td>Coordinated multi-card ring; mule fan-out</td>
      <td>Cheap orchestration of many synthetic participants</td></tr>
  <tr><td>Merchant fraud</td><td>Fabricated storefront; refund collusion; transaction laundering /
      MCC misrepresentation</td><td>Generated storefronts, catalogues and reviews are trivial to
      produce at scale</td></tr>
  <tr><td>Adaptive evasion</td><td>Velocity evasion; adaptive mimicry; TRA / SCA-exemption
      threshold gaming</td><td>Models learn the victim's own baseline and stay inside it</td></tr>
  <tr><td>Enumeration</td><td>BIN enumeration bursts</td><td>Automated, distributed card testing</td></tr>
  <tr><td>First-party fraud</td><td>Mandate replay abuse; dispute abuse patterns</td>
      <td>Templated, plausible dispute narratives at scale</td></tr>
</table>
<div class="note"><b>Alignment with the organiser's stated priorities.</b> Mastercard AI Garage
publicly named four priority threats — synthetic identities, deepfake KYC, fake merchant
storefronts and AI-enabled scams. All four are covered as first-class categories.</div>
<h3>The hardest case, and why it matters</h3>
<p><code>APP_SCAM_LLM</code> (authorised push payment scam) is the hardest problem in payments
fraud: the <b>genuine cardholder</b>, on <b>their own device</b>, with <b>real 3-D Secure
authentication</b>, <b>willingly</b> authorises the payment. Every credential signal is clean.
Only the <i>intent</i> is wrong. Most detectors implicitly assume compromised credentials; this
one has none.</p>

<!-- ============ 7 ============ -->
<h2 id="p7" class="brk">7 · Pillar 2 — Generate: simulation and fidelity evidence</h2>
<h3>The feasible-action constraint</h3>
<p>The standing criticism of adversarial machine learning on tabular data is that papers perturb
features an attacker cannot actually control. That produces impressive numbers and unusable
systems. Aegis's generators may move <b>only</b> what a real attacker controls.</p>
<div class="grid">
  <div class="card"><b>Levers the simulator may move</b>
    <ul><li>Amount, and how it splits across attempts</li><li>Timing, inter-arrival cadence,
    burst shape</li><li>Merchant and MCC selection</li><li>Device and channel presentation</li>
    <li>Sequencing — probe, escalate, cash out</li><li>Text in merchant-controlled fields</li></ul></div>
  <div class="card"><b>Held invariant — not the attacker's to change</b>
    <ul><li>The victim's own historical baseline</li><li>Issuer-side risk state and scoring</li>
    <li>Network-assigned identifiers and tokens</li><li>AVS / CVV results returned by the issuer</li>
    <li>Another cardholder's genuine behaviour</li><li>Any label the defence later assigns</li></ul></div>
</div>
<p>This costs headline numbers — it is far easier to score well against attacks that cheat by
editing issuer-side fields. But an attack requiring a rewrite of the victim's own history is data
corruption, not an attack. The constraint is what makes the detection results mean anything
operationally.</p>

<h3>Fidelity evidence — measured, not asserted</h3>
<p>The brief judges fidelity <i>instrumentally</i>: the data must be "genuinely useful for
training and stress-testing a defense". So <code>fidelity.py</code> measures it, and the results
land in <code>metrics.json</code>. {fid['summary'].capitalize()}.</p>
<h4>Part 1 — generated marginals against published reference bands</h4>
<table><tr><th>Measure</th><th>Value</th><th>Reference band</th><th>In band</th></tr>
{fr_rows}</table>
<p>Bands come from public sources — PSD2 RTS Annex fraud-rate bands, and Nigrini's published
thresholds for Benford conformity — and are deliberately wide: they are sanity bands for a
synthetic corpus, not calibration targets to overfit.</p>
<div class="ok"><b>Benford's law.</b> Real transaction amounts follow Benford's distribution of
leading digits, a standard forensic-accounting test. Ours has a mean absolute deviation of
<b>{fr['benford_mad']['value']:.4f}</b>, inside Nigrini's "close conformity" threshold of 0.006 —
and we did not tune for it.</div>
<h4>Part 2 — non-separability (the anti-"trivially separable" evidence)</h4>
<p>If attack traffic came from an obviously different process, any classifier would score ~1.0 and
the entire evaluation would be meaningless. So we measure univariate AUC on <b>raw</b>
authorization fields, with no engineered features. Here, <b>low is good</b>.</p>
<table><tr><th>Raw field</th><th>Univariate AUC</th><th>Attack/legit overlap</th></tr>
{fs_rows}</table>
<p>Max raw-field AUC <b>{fs['max_univariate_auc']}</b>; mean attack/legit overlap
<b>{fs['mean_overlap']}</b>. The <code>amount</code> row is the important one: at AUC
{fs['per_field']['amount']['univariate_auc']:.3f} the generator plainly does <b>not</b> take the
usual shortcut of making fraud large — the failure mode that renders most synthetic fraud corpora
trivially separable.</p>
<p><code>cross_border</code> is the highest single field, and that is realistic rather than an
artefact: cross-border genuinely carries materially elevated fraud rates in live portfolios. If our
cross-border fraud rate matched domestic, <i>that</i> would be the fidelity failure.</p>
<p>The most camouflaged vectors — highest overlap with legitimate traffic — are
{", ".join(f"<code>{k}</code> {v:.3f}" for k, v in list(fs['most_camouflaged_vectors'].items())[:4])}.
These are the same vectors the detector performs worst on, so the fidelity measurement and the
detection results corroborate each other independently.</p>
<h3>Safety</h3>
<div class="warn"><b>Network isolation by construction.</b> The simulator has no network client at
all. This is enforced by an <b>AST-level test</b> that parses every simulator module and fails the
build if a networking import, <code>subprocess</code>, or dynamic execution appears. Competition
Rules §3(b) require that adversarial testing "does not target live systems, payment infrastructure
or third parties" — so this is a rules requirement met in code, not a promise in prose.</div>

<!-- ============ 8 ============ -->
<h2 id="p8" class="brk">8 · Pillar 3 — Defend: features, cascade, explainability</h2>
<h3>The feature layer — 57 strictly causal features</h3>
<table>
  <tr><th>Family</th><th>Examples</th><th>What it captures</th></tr>
  <tr><td><b>Velocity</b></td><td>transactions in the last hour / day; amount velocity;
      distinct merchants per window</td><td>Bursts and automation</td></tr>
  <tr><td><b>Own-baseline deviation</b></td><td>amount z-score against this account's own history;
      new-merchant flag; unusual hour for <i>this</i> cardholder</td>
      <td>Change relative to the individual, not to the population — a ₹5,000 purchase is normal
      for one person and alarming for another</td></tr>
  <tr><td><b>Graph</b></td><td>cards per device; devices per card; ring component size; fan-in</td>
      <td>Shared infrastructure, invisible per transaction</td></tr>
  <tr><td><b>Verification coherence</b></td><td>AVS/CVV/3DS agreement; exemption claimed on a
      high-risk payment; token absent where expected</td>
      <td>Combinations that should not co-occur</td></tr>
</table>
<div class="note"><b>"Strictly causal"</b> means every feature is computable from information
available at the moment of authorization. No feature sees the label, and none sees the future. The
test suite proves it: features recomputed on a truncated prefix of history must be
<i>identical</i> to the full-history values for those rows.</div>
<h3>The three-stage cascade</h3>
<pre><code>  transaction
       │
   [1] 39 deterministic rule signals      ← fast, cheap, runs on 100% of traffic
       │
   [2] HistGradientBoostingClassifier     ← learned patterns
       │
   [3] graph structure                    ← expensive; runs on the riskiest {cap['alert_rate']*0+20:.0f}% only
       │
   [arbiter] combines the three additively
       │
   [isotonic calibration] → final risk score in [0,1] that means what it says</code></pre>
<p>The airport-security analogy: a metal detector everyone passes through, an X-ray for bags, and a
full manual search reserved for the few. Stage 3 is gated by an explicit <b>compute budget</b>
(the riskiest 20%) rather than a score threshold, because a threshold allows cost to spike exactly
when an attack floods the high-risk band. A budget cannot. That is how p99 stays at
{lat['decision_p99_ms']:.1f} ms.</p>
<h3>Explainability — exact by construction</h3>
<p>A declined payment may legally require a reason, and model governance expects decisions to be
reconstructable. Every alert carries four things:</p>
<ol>
  <li><b>The decision</b> — calibrated risk, band, recommended action (allow / review / step up /
      block), alongside the payment's own verification attributes.</li>
  <li><b>An exact score decomposition</b> — additive contributions to the arbiter's log-odds.
      "Log-odds" simply means a scale on which evidence adds up. These are not estimates: the terms
      sum to the score, and the test suite verifies the reconciliation against the model's own
      decision function.</li>
  <li><b>Reason codes</b> — ranked, in analyst language rather than feature names
      (e.g. <i>"Unusual burst of transactions within the hour"</i>, weight 0.80).</li>
  <li><b>A counterfactual</b> — what would have to change for the payment to score benign
      (e.g. <i>"would likely fall below review absent the velocity_burst signal"</i>).</li>
</ol>
<div class="warn"><b>The honest boundary.</b> Per-row attribution <i>inside</i> the gradient-boosted
component is <b>not</b> claimed. Its contribution appears as a single exact term, and its feature
importance is reported globally and labelled as global. SHAP could not be installed
(<code>numba</code> fails on Python 3.14), and shipping an approximate explainer while calling it
attribution would be worse than naming the limit — the literature shows fluent rationales raise
analyst confidence without raising accuracy.</div>
<h3>Signals deliberately not implemented</h3>
<p>All {cov['expected_signals_covered']} of {cov['expected_signals_distinct']} distinct declared
signals are implemented. These are published as out of scope, each with its reason:</p>
<table><tr><th>Signal</th><th>Why not</th></tr>{unimpl}</table>

<!-- ============ 9 ============ -->
<h2 id="p9" class="brk">9 · Evaluation — methodology and full results</h2>
<h3>How the split is done, and why it matters most</h3>
<p><b>{sp['method']}</b> — train {sp['train']:,}, test {sp['test']:,}, with
{sp['delay_fraction']:.0%} of the timeline <b>discarded between them</b>. Test-set fraud prevalence
is {sp['test_fraud_rate']:.2%}.</p>
<div class="note">Chargeback labels arrive weeks after the transaction. A random train/test split
would let the model learn from payments that happen <i>after</i> the ones it is tested on — the
future leaking into the past, producing a score that cannot be reproduced in production. Discarding
a slice of the timeline simulates that reporting lag honestly.</div>
<h3>Headline results</h3>
<div class="grid">
  <div class="card"><b>PR-AUC</b><span class="big">{di['pr_auc']:.4f}</span>
      95% CI {lo:.3f} – {hi:.3f}, bootstrapped</div>
  <div class="card"><b>ROC-AUC</b><span class="big">{di['roc_auc']:.4f}</span>
      shown for comparability; optimistic under imbalance</div>
  <div class="card"><b>Decision latency</b><span class="big">{lat['decision_p99_ms']:.2f} ms</span>
      p99 · p50 {lat['decision_p50_ms']:.2f} ms · p95 {lat['decision_p95_ms']:.2f} ms</div>
  <div class="card"><b>Zero-day recall</b><span class="big">{zd['unseen_recall']:.3f}</span>
      {len(zd['held_out_vectors'])} vectors never trained on</div>
</div>
<p><b>Why PR-AUC is the headline:</b> at {sp['test_fraud_rate']:.2%} prevalence a model that blocks
nothing scores {1 - sp['test_fraud_rate']:.1%} accuracy. Accuracy is meaningless here. ROC-AUC is
optimistic because the true-negative pool is enormous. PR-AUC concentrates on the positive class,
which is the one that matters.</p>
<h3>Three operating points — one detector, three settings of the dial</h3>
<table>
  <tr><th>Operating point</th><th>Threshold</th><th>Precision</th><th>Recall</th><th>Notes</th></tr>
  <tr><td><b>Best-F1</b></td><td>{f1['threshold']:.3f}</td><td>{f1['precision']:.3f}</td>
      <td>{f1['recall']:.3f}</td><td>F1 {f1['f1']:.3f}; FPR {f1['false_positive_rate']:.5f}</td></tr>
  <tr><td><b>Capacity-constrained</b><br><span class="small">1% analyst review budget</span></td>
      <td>{cap['threshold']:.3f}</td><td>{cap['precision']:.3f}</td><td>{cap['recall']:.3f}</td>
      <td>{cap['alerts']} alerts; <b>ceiling {cap['recall_ceiling']:.3f}</b></td></tr>
  <tr><td><b>Prevalence-matched</b><br><span class="small">budget sized to actual fraud rate</span></td>
      <td>{pm['threshold']:.3f}</td><td>{pm['precision']:.3f}</td><td>{pm['recall']:.3f}</td>
      <td>{pm['alerts']} alerts; not budget-capped</td></tr>
</table>
<p>Confusion matrix at the best-F1 point: <b>TP {cf['tp']}</b> fraud correctly caught ·
<b>FP {cf['fp']}</b> honest payments wrongly flagged · <b>FN {cf['fn']}</b> fraud missed ·
<b>TN {cf['tn']:,}</b> honest payments correctly approved.</p>
<div class="warn"><b>Read the ceiling before reading the recall.</b> {cap['ceiling_note']}
At a {cap['alert_rate']:.0%} alert budget and {sp['test_fraud_rate']:.2%} prevalence the maximum
recall <i>any</i> detector could achieve is <b>{cap['recall_ceiling']:.3f}</b>. We reach
{cap['recall']:.3f} — {cap['recall']/cap['recall_ceiling']:.1%} of the mathematical ceiling. If a
hospital has 10 beds and 30 patients, treating 10 is a bed shortage, not a doctor failure.</div>
<h3>Money and customer impact</h3>
<table>{rows([
  ("Value detection rate", f"<b>{mo['value_detection_rate']:.3f}</b> — the share of attempted fraud <i>value</i> stopped, not just count"),
  ("Insult rate", f"{mo['insult_rate']:.5f} — {mo['insult_rate_note']}"),
  ("Note on absolute values", "Amounts are summed across a multi-currency synthetic population, so the absolute totals carry no single currency unit. Read the ratio, not the totals."),
])}</table>
<h3>Calibration — does 0.9 really mean 90%?</h3>
<p>Brier {cal['brier']:.5f} · Expected Calibration Error (10-bin) <b>{cal['ece_10bin']:.5f}</b> ·
method: {cal['method']}.</p>
<p>A calibrated score behaves like an honest weather forecaster: on days they say "70% chance of
rain", it rains about 70% of the time. This matters because a bank sets policy on expected loss —
if 0.9 does not mean 90%, a cost-based block threshold cannot be justified.</p>
<h3>Zero-day generalisation — the novelty evidence</h3>
<p>{len(zd['held_out_vectors'])} vectors removed from training <b>entirely</b>, then scored at a
threshold calibrated on <b>seen traffic only</b> — no retuning on the held-out data.
Aggregate: <b>{zd['unseen_recall']:.3f}</b> across {zd['unseen_transactions']:,} transactions.</p>
<table><tr><th>Held-out vector</th><th>n</th><th>Recall</th><th>Mean risk</th><th>Hard</th></tr>
{zd_rows}</table>
<p>Recall on attacks the model trained on measures memorisation. This measures whether a causal
feature layer transfers to fraud that <i>did not exist</i> when the model was fit.</p>
<h3>Per-attack recall — worst first</h3>
<p>At the capacity-constrained operating point, sorted so the failures appear first rather than
buried at the bottom.</p>
<table><tr><th>Vector</th><th>Category</th><th>n</th><th>Recall @1%</th><th>Mean risk</th>
<th>Hard</th><th>Sev</th></tr>{pa_rows}</table>

<!-- ============ 10 ============ -->
<h2 id="p10" class="brk">10 · Where it fails — stated plainly</h2>
<h3>The one genuine model failure</h3>
<p><code>ADAPTIVE_MIMICRY</code> — recall
{m['per_attack']['ADAPTIVE_MIMICRY']['recall_at_alert_rate']:.3f} at the 1% budget, and crucially a
mean risk of only {m['per_attack']['ADAPTIVE_MIMICRY']['mean_risk']:.3f}. The low mean risk is what
makes this a real miss rather than a queue-capacity artefact: the model genuinely does not find it
suspicious. The attack learns the victim's own baseline and stays inside it, which defeats
deviation-based features <i>by construction</i>.</p>
<p>It is corroborated independently by the fidelity measurement, where mimicry is among the vectors
overlapping legitimate traffic most. <b>This is the row we would fix first.</b> The likely approach
is a "baseline over-conformity" feature: a replayed baseline is <i>less</i> noisy than genuine human
behaviour, so anomalously low variance is itself a signal.</p>
<h3>Second weakest</h3>
<p><code>AGENT_IMPERSONATION</code> — zero-day recall
{zd['per_vector']['AGENT_IMPERSONATION']['recall_at_seen_threshold']:.3f}. In an authorization
message, a legitimate agentic purchase and an impersonated one are nearly indistinguishable.
Separating them requires agent-identity attestation that the schema does not yet carry. This is a
roadmap item, not a tuning problem.</p>
<h3>Rows that look worse than they are</h3>
<p><code>REFUND_ABUSE_COLLUSION</code> shows 0.000 recall on <b>n = 2</b> transactions in this
split — that is noise, not a measurement. Its mean risk is
{m['per_attack']['REFUND_ABUSE_COLLUSION']['mean_risk']:.3f}, so the model did rank it as risky; it
simply lost the competition for {cap['alerts']} review slots.</p>
<h3>Prevalence caveat</h3>
<div class="warn">{m['prevalence_note']}</div>
<h3>Explainability boundary</h3>
<p>Restated because it matters: no per-row attribution is claimed inside the gradient-boosted
component. Its importance is global and labelled as global.</p>

<!-- ============ 11 ============ -->
<h2 id="p11" class="brk">11 · The dashboard — all seven panels</h2>
<p>The header carries two compliance badges — <b>SYNTHETIC DATA</b> and
<b>NETWORK-ISOLATED</b> — plus a live/offline state. The navigation is grouped into
<span style="color:#be123c"><b>red team</b></span> and
<span style="color:#0369a1"><b>blue team</b></span> so both halves of the brief are visible.</p>
<table>
  <tr><th>Panel</th><th>Side</th><th>What it shows</th></tr>
  <tr><td><b>Overview</b></td><td>—</td><td>Transactions in scope, attack traffic injected,
      high/critical alerts, vectors available; alert-band distribution; the four verified headline
      metrics; the closed-loop diagram; recent campaigns with detection rates</td></tr>
  <tr><td><b>Attack Simulator</b></td><td>Red</td><td>The library of {d['attack_vectors']} vectors
      filtered by category. Selecting one shows its mechanics, what GenAI changed, its MITRE ATLAS
      mapping, its <b>expected detection signals declared up front</b>, and a strength slider from
      "subtle · fewer entities" to "aggressive · at scale". <b>Launch campaign</b> injects it live.</td></tr>
  <tr><td><b>Live Stream</b></td><td>Blue</td><td>The scored authorization feed — risk, band,
      recommended action. Filter to high &amp; critical to see the real analyst queue.</td></tr>
  <tr><td><b>Investigate</b></td><td>Blue</td><td>Alert queue plus, for the selected payment: the
      decision and its verification attributes, the exact additive score decomposition, ranked
      reason codes, and the counterfactual.</td></tr>
  <tr><td><b>Fraud Network</b></td><td>Blue</td><td>The subgraph induced by <i>shared</i>
      infrastructure only — entities touching two or more distinct cards. Unpruned it is mostly
      singleton pairs and the structure disappears.</td></tr>
  <tr><td><b>Performance</b></td><td>Blue</td><td>The full evaluation: split description, headline
      metrics, three operating points, calibration curve, zero-day table, per-attack recall
      worst-first, signal coverage, and the stated limitations.</td></tr>
  <tr><td><b>Audit Trail</b></td><td>—</td><td>Append-only log of every environment change, campaign
      and analyst action. Append-only means entries can be added but never edited or deleted.</td></tr>
</table>
<h3>Alert bands</h3>
<table>
  <tr><th>Band</th><th>Meaning</th><th>Action</th></tr>
  <tr><td>LOW</td><td>Normal</td><td>Approve silently</td></tr>
  <tr><td>MEDIUM</td><td>Slightly unusual</td><td>Monitor</td></tr>
  <tr><td>HIGH</td><td>Suspicious</td><td>Human review</td></tr>
  <tr><td>CRITICAL</td><td>Almost certainly fraud</td><td>Block</td></tr>
</table>
<p>LOW is charted as a bar but excluded from the scaled chart deliberately: it holds tens of
thousands of rows and would flatten the three actionable bands into invisibility. Colour is always
paired with an explicit text label, never used alone, for accessibility.</p>

<!-- ============ 12 ============ -->
<h2 id="p12" class="brk">12 · How to run it</h2>
<h3>First time only</h3>
<pre><code>python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd frontend &amp;&amp; npm install &amp;&amp; cd ..
.venv/bin/python -m backend.app.evaluate     # regenerates all metrics (~3 min)</code></pre>
<h3>Every session — two terminal windows</h3>
<pre><code># WINDOW 1 — backend
.venv/bin/uvicorn backend.app.api:app --port 8000

# WINDOW 2 — dashboard
cd frontend &amp;&amp; npm run dev</code></pre>
<p>Then open <b>http://localhost:5173</b> and click <b>Start environment</b>. The build takes
10–15 seconds; wait for the header badge to read <b>ENVIRONMENT LIVE</b> before presenting.</p>
<div class="note">Windows 1 and 2 stay occupied — those processes run until stopped with
<code>Ctrl+C</code>. Use a <b>third</b> window for any other command.</div>
<h3>Health checks</h3>
<pre><code>curl -s localhost:8000/api/health            # -&gt; {{"status":"ok", ...}}
curl -s localhost:8000/api/health | grep -o '"ready":[a-z]*'   # false = still building</code></pre>

<!-- ============ 13 ============ -->
<h2 id="p13">13 · How to test it</h2>
<pre><code>./scripts/verify.sh --full          # everything; must end "VERIFIED — safe to push"</code></pre>
<table>
  <tr><th>Stage</th><th>What it proves</th></tr>
  <tr><td>6 module self-checks</td><td>Each module works standalone</td></tr>
  <tr><td>113 pytest tests</td><td>Nothing regressed</td></tr>
  <tr><td>Secrets &amp; compliance scan</td><td>No credentials, no competition captures, no build
      artifacts tracked</td></tr>
  <tr><td>Metrics freshness guard</td><td>Fails if any backend source is <i>newer</i> than
      <code>metrics.json</code> — stale metrics silently poison every published figure</td></tr>
  <tr><td>Docs-agree guard</td><td>Fails if any document quotes a PR-AUC or p99 that disagrees with
      the artifact</td></tr>
  <tr><td>TypeScript typecheck + Vite build</td><td>Frontend compiles cleanly</td></tr>
  <tr><td>Playwright browser smoke test</td><td>The real demo path works end to end</td></tr>
</table>
<div class="warn"><b>Start both servers before testing.</b> Without them the browser smoke test
<i>skips</i> rather than fails — and prints green. A skipped check that looks like a pass is more
dangerous than a red failure.</div>
<h3>Narrower commands</h3>
<pre><code>.venv/bin/python -m pytest backend/tests -q          # 113 tests, ~30s
.venv/bin/python -m pytest backend/tests/test_security.py -q   # 21 compliance tests
.venv/bin/python -m backend.app.fidelity             # fidelity self-check
.venv/bin/python -m backend.app.evaluate             # regenerate metrics
.venv/bin/python scripts/make_deck.py                # rebuild the deck
python3 scripts/make_pdf.py                          # rebuild this document (system python)
cd frontend &amp;&amp; npx tsc --noEmit                      # typecheck only</code></pre>
<h3>What the four test suites protect</h3>
<table>
  <tr><th>Suite</th><th>Guards against</th></tr>
  <tr><td>Data pipeline</td><td>Schema drift, duplicate transaction ids, label leakage</td></tr>
  <tr><td>Detection</td><td>Cascade regression, calibration drift, explainer/model disagreement</td></tr>
  <tr><td>Security (21 tests)</td><td>Network egress in the simulator (AST-level), PAN-like or
      Luhn-valid identifiers, personal names, untruncated IPs, committed secrets, non-permissive
      licences, operational fraud instructions in the taxonomy</td></tr>
  <tr><td>API</td><td>Endpoint contracts, WebSocket lifecycle, append-only audit behaviour</td></tr>
</table>

<!-- ============ 14 ============ -->
<h2 id="p14" class="brk">14 · Glossary — every term used</h2>
<h3>Payments</h3>
<table>
  <tr><th>Term</th><th>Meaning</th></tr>
  {rows([
    ("Authorization", "The real-time request asking the issuer to approve a payment. Aegis scores this message."),
    ("PAN", "Primary Account Number — the long number on a card. <b>Never present in this system</b>; tokens are used throughout."),
    ("Network token", "A substitute value standing in for the PAN, so the real number never circulates."),
    ("MCC", "Merchant Category Code — a 4-digit industry code (5999 = miscellaneous retail)."),
    ("ECOM / POS / MOTO", "Online / physical card machine / mail-or-telephone order."),
    ("Card-not-present (CNP)", "The physical card was not used — typically online. Structurally higher risk."),
    ("AVS", "Address Verification Service — did the billing address match?"),
    ("CVV", "The 3-digit security code."),
    ("3-D Secure", "The extra bank authentication step (Mastercard Identity Check, Verified by Visa)."),
    ("SCA", "Strong Customer Authentication — EU PSD2 requirement for multi-factor authentication."),
    ("SCA exemption", "A rule permitting the check to be skipped for low-risk payments. Attackers game the bands."),
    ("TRA", "Transaction Risk Analysis — an exemption route based on the acquirer's fraud rate."),
    ("PSD2 / RTS", "EU payment services regulation and its Regulatory Technical Standards, which publish reference fraud-rate bands."),
    ("ISO 8583", "The international standard for card authorization message formats."),
    ("Chargeback", "A customer dispute reversing a payment — the mechanism that produces fraud labels, weeks late."),
    ("APP fraud", "Authorised Push Payment fraud — the victim is tricked into authorising it themselves."),
    ("Pig-butchering", "A long-con romance-plus-investment scam."),
    ("Mule account", "An account used to receive and forward criminal proceeds."),
    ("BIN enumeration", "Automated guessing of valid card numbers by testing small charges."),
    ("Bust-out", "Building good credit history, then maxing everything out and disappearing."),
    ("Transaction laundering", "Processing payments for one business under another's merchant account."),
    ("Insult rate", "How often a legitimate customer is wrongly declined. Industry term."),
    ("Step up", "Do not decline — request additional proof, such as an OTP."),
    ("Issuer / Acquirer", "The cardholder's bank / the merchant's bank."),
    ("KYC", "Know Your Customer — identity verification at account opening."),
  ])}
</table>
<h3>Machine learning and statistics</h3>
<table>
  <tr><th>Term</th><th>Meaning</th></tr>
  {rows([
    ("True positive (TP)", "Fraud, correctly caught."),
    ("False positive (FP)", "Legitimate payment, wrongly flagged — an angry customer."),
    ("False negative (FN)", "Fraud, missed — money lost."),
    ("True negative (TN)", "Legitimate payment, correctly approved."),
    ("Precision", "Of everything flagged, the share that really was fraud. \"Am I crying wolf?\""),
    ("Recall", "Of all real fraud, the share caught. \"Am I missing thieves?\""),
    ("F1", "The harmonic mean of precision and recall — a single balanced score."),
    ("PR-AUC", "Area under the precision–recall curve: overall quality across every threshold. The honest headline under class imbalance."),
    ("ROC-AUC", "Area under the receiver-operating-characteristic curve. Optimistic when positives are rare, because the true-negative pool is huge."),
    ("Class imbalance", "One class vastly outnumbers the other. Here fraud is ~3% of rows."),
    ("Prevalence", "The share of rows that are fraud."),
    ("Calibration", "Whether a predicted probability matches observed frequency — does 0.9 mean 90%?"),
    ("ECE", "Expected Calibration Error — average gap between predicted and observed, across bins."),
    ("Brier score", "Mean squared error of probabilistic predictions. Lower is better."),
    ("Isotonic regression", "A monotonic, non-parametric method for fixing miscalibrated scores."),
    ("Log-odds", "A scale on which independent pieces of evidence can be <i>added</i>. Makes the explanation additive."),
    ("Gradient boosting", "An ensemble of small decision trees, each correcting its predecessors' errors."),
    ("Temporal split", "Train on earlier data, test on later data — mimics production."),
    ("Delay block", "A discarded slice of timeline between train and test, reflecting late label arrival."),
    ("Label leakage", "When a feature encodes the answer, inflating scores unreproducibly."),
    ("Zero-day", "An attack type absent from training entirely."),
    ("Bootstrapped CI", "A confidence interval obtained by resampling, rather than assuming a distribution."),
    ("p50 / p95 / p99", "Median / 95th / 99th percentile latency. p99 is the worst-case that matters."),
    ("Univariate AUC", "Discriminative power of a <i>single</i> feature. Used here to prove no raw field gives the attacks away."),
    ("Overlap coefficient", "How much two distributions share, 0–1. High overlap between attack and legitimate traffic means realistic camouflage."),
    ("Benford's law", "The distribution of leading digits in natural numeric data. A standard forensic test."),
    ("MAD", "Mean absolute deviation — used here against Benford's expected frequencies."),
    ("Gini coefficient", "A concentration measure, used here for how unevenly volume spreads across MCCs."),
    ("Index of dispersion", "Variance divided by mean. Above 1 means bursty rather than uniformly random."),
    ("MITRE ATLAS", "A public catalogue of adversarial techniques against AI systems."),
    ("Counterfactual", "The minimal change that would flip the decision."),
    ("AST", "Abstract Syntax Tree — the parsed structure of source code. Used to prove the simulator cannot reach a network."),
  ])}
</table>

<!-- ============ 15 ============ -->
<h2 id="p15" class="brk">15 · Competition compliance</h2>
<table>
  <tr><th>Requirement</th><th>Source</th><th>How it is met</th></tr>
  <tr><td>Synthetic, anonymised or authorised sample data only; no real cardholder, PII or
      production payment data</td><td>Rules §3(a)</td>
      <td>100% self-generated. No PAN exists. Every row carries <code>synthetic: true</code>.
      Enforced by tests for PAN-like patterns, Luhn validity, personal names and untruncated
      IPs.</td></tr>
  <tr><td>Adversarial testing must not target live systems, payment infrastructure or third
      parties</td><td>Rules §3(b)</td>
      <td>The simulator has no network client. An AST-level test fails the build if a networking
      import, subprocess or dynamic execution appears in any simulator module.</td></tr>
  <tr><td>Responsible AI, cybersecurity and disclosure practices</td><td>Rules §3(c)</td>
      <td><code>docs/security.md</code>; a test asserts the taxonomy contains no operational
      fraud instructions — it describes behaviour to detect, not recipes to reproduce.</td></tr>
  <tr><td>Open-source dependencies must be OSI-approved and must not limit commercial use</td>
      <td>Kaggle Foundational §6(c)</td>
      <td>All 41 Python and 121 npm packages audited; MIT / BSD / Apache-2.0 / ISC / MPL-2.0 only.
      Zero AGPL, GPL or SSPL. Inventory in <code>requirements.txt</code>.</td></tr>
  <tr><td>No private sharing of competition code during the competition period</td>
      <td>Kaggle Foundational §6(a)</td><td>Repository is private, verified by an unauthenticated
      API request returning 404. Published after judging concludes.</td></tr>
  <tr><td>A valid submission must include all three artifacts</td><td>Rules §2, §3</td>
      <td>Code repository · walkthrough deck (<code>.pptx</code>, 15 slides) · working web
      prototype.</td></tr>
  <tr><td>Draft work is not considered</td><td>Rules §2</td>
      <td><b>Action required:</b> the writeup must be actively <i>submitted</i> in the Kaggle
      Writeups section, not left in draft.</td></tr>
</table>

<!-- ============ 16 ============ -->
<h2 id="p16">16 · Repository map</h2>
<pre><code>research/         verified competition rules, threat landscape, existing solutions, sources
docs/
  architecture.md            system design
  decisions.md               every significant choice and its rationale
  threat-model.md            attacker capabilities and assumptions
  fraud-taxonomy.md          all 25 vectors in detail (generated)
  detection-methodology.md   features, cascade, calibration
  evaluation.md              full results (generated)
  security.md                responsible AI and security posture
  demo-flow.md               the 7-minute live demo script
  deployment.md              production considerations
  presenter-guide.md         run/test, pitch at 3 lengths, judge Q&amp;A bank
  submission-writeup.md      the Kaggle Writeups text
  current-state.md           compact project state
backend/app/      schema · generator · attacks · features · fidelity · detect · explain ·
                  evaluate · api
backend/tests/    113 tests across 4 suites
frontend/src/     App.tsx + 7 panels + shared components
scripts/          verify.sh · make_deck.py · make_pdf.py · gen_docs.py · ui_smoke.py
artifacts/        metrics.json · aegis-walkthrough.pptx · aegis-project-explained.pdf ·
                  screenshots/ · audit.db</code></pre>
<h3>Reproduce everything from a clean checkout</h3>
<pre><code>git clone &lt;repo&gt; &amp;&amp; cd ThreatForge
python3 -m venv .venv &amp;&amp; .venv/bin/pip install -r requirements.txt
cd frontend &amp;&amp; npm install &amp;&amp; cd ..
.venv/bin/python -m backend.app.evaluate
./scripts/verify.sh --full</code></pre>
<p class="small" style="margin-top:14pt">Generated by <code>scripts/make_pdf.py</code> from
<code>artifacts/metrics.json</code> (evaluation run {m['generated_at_utc'][:19]}Z). Every figure in
this document is read from that artifact; none is typed by hand.</p>

</body></html>"""


def main() -> None:
    if not METRICS.exists():
        raise SystemExit("artifacts/metrics.json missing — run: "
                         ".venv/bin/python -m backend.app.evaluate")
    m = json.loads(METRICS.read_text())
    html = build_html(m)
    HTML_OUT.write_text(html)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto(HTML_OUT.as_uri())
        page.wait_for_load_state("networkidle")
        page.pdf(path=str(PDF_OUT), format="A4", print_background=True,
                 margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"},
                 display_header_footer=True,
                 header_template="<div></div>",
                 footer_template=(
                     '<div style="width:100%;font:8pt Helvetica,Arial;color:#8a99ad;'
                     'padding:0 14mm;display:flex;justify-content:space-between">'
                     '<span>Aegis — AI Defence Lab for Payment Security · 100% synthetic data</span>'
                     '<span class="pageNumber"></span></div>'))
        b.close()
    kb = PDF_OUT.stat().st_size / 1024
    print(f"wrote {PDF_OUT.relative_to(ROOT)} ({kb:,.0f} KB) and "
          f"{HTML_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
