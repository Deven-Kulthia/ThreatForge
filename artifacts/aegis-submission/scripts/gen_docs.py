"""Generate docs/fraud-taxonomy.md from the code.

The taxonomy lives in `backend/app/attacks.py`. Hand-maintaining a parallel markdown
table guarantees drift, so the document is generated instead — and CI can regenerate it
to prove code and docs agree.

    .venv/bin/python -m scripts.gen_docs        (or: .venv/bin/python scripts/gen_docs.py)
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.attacks import SIMULATORS, TAXONOMY  # noqa: E402
from backend.app.detect import RULE_NAMES, UNIMPLEMENTED_SIGNALS  # noqa: E402

DOCS = ROOT / "docs"


def main() -> None:
    by_cat: dict[str, list] = defaultdict(list)
    for s in TAXONOMY.values():
        by_cat[s.category].append(s)

    graph_signals = {"ring_component", "graph_fanin", "injection_pattern_in_text"}
    all_expected = {sig for s in TAXONOMY.values() for sig in s.expected_signals}
    implemented = {s for s in all_expected if s in RULE_NAMES or s in graph_signals}

    out: list[str] = [
        "# Fraud Taxonomy",
        "",
        "**Generated from `backend/app/attacks.py` — do not edit by hand.**",
        "Regenerate with `.venv/bin/python scripts/gen_docs.py`.",
        "",
        f"**{len(TAXONOMY)} attack vectors across {len(by_cat)} categories.** Every vector has a "
        "working simulator, is mapped to MITRE ATLAS or ATT&CK, states what generative AI "
        "specifically changed about it, and declares the signals a competent detector ought "
        "to fire on.",
        "",
        "## Why declared signals matter",
        "",
        "Each vector's `expected_detection_signals` are ground truth for *detectability*, not "
        "just for the label. That lets the evaluation harness measure whether an attack was "
        "caught **for the right reason** rather than by coincidence — reported as per-signal "
        "recall in `artifacts/metrics.json`.",
        "",
        "## Design principle: feasible-action attacks",
        "",
        "The standing criticism of adversarial ML on tabular data is that it perturbs features "
        "an attacker cannot control. You cannot set `amount = 43.7291`, and you certainly "
        "cannot forge an EMV application transaction counter. Every attack here is restricted "
        "to the attacker's real action space:",
        "",
        "| Attacker controls | Never forged |",
        "|---|---|",
        "| amount, timing, cadence | issuer-side verification results |",
        "| merchant and MCC selection | cryptogram validity |",
        "| channel, device, IP, user agent | transaction counters |",
        "| which card is used, sequencing across cards | network token assurance level |",
        "",
        "Where an attack *does* alter a verification field, it is because the real attack path "
        "genuinely produces that outcome — an intercepted OTP legitimately yields a 3-D Secure "
        "`AUTHENTICATED` status, which is precisely why OTP interception is dangerous.",
        "",
        "## Safety boundary",
        "",
        "Attacks are modelled purely as **observable behavioural change in a transaction "
        "stream** — the level a defender needs to build detection, and nothing lower. This "
        "repository contains no operational instructions for committing fraud. The simulator "
        "operates only on in-process synthetic data and imports no network capability; "
        "`backend/tests/test_security.py` proves this by parsing the modules with `ast`.",
        "",
        "---",
        "",
        "## Coverage summary",
        "",
        "| Category | Vectors | Hard by design | Max severity |",
        "|---|---|---|---|",
    ]

    for cat in sorted(by_cat):
        specs = by_cat[cat]
        hard = sum(1 for s in specs if s.hard_to_detect)
        out.append(f"| {cat} | {len(specs)} | {hard} | {max(s.severity for s in specs)}/5 |")

    hard_total = sum(1 for s in TAXONOMY.values() if s.hard_to_detect)
    out += [
        f"| **Total** | **{len(TAXONOMY)}** | **{hard_total}** | — |",
        "",
        f"**Signal coverage:** {len(implemented)} of {len(all_expected)} distinct expected "
        f"signals are implemented as detectors ({len(RULE_NAMES)} rule signals plus "
        f"{len(graph_signals)} emitted by the graph and text-safety stages).",
        "",
        "Signals deliberately **not** implemented, and why — stated so per-signal recall is "
        "read honestly rather than looking like a silent miss:",
        "",
    ]
    for sig, reason in sorted(UNIMPLEMENTED_SIGNALS.items()):
        out.append(f"- `{sig}` — {reason}")

    out += ["", "---", "", "## Vectors by category", ""]

    for cat in sorted(by_cat):
        out += [f"### {cat}", ""]
        for s in sorted(by_cat[cat], key=lambda x: -x.severity):
            hard = " · **hard by design**" if s.hard_to_detect else ""
            out += [
                f"#### {s.name}",
                "",
                f"`{s.id}` · severity **{s.severity}/5** · channels {', '.join(s.channels)}{hard}",
                "",
                s.description,
                "",
                f"**What GenAI changed.** {s.genai_role}",
                "",
                f"**Framework alignment.** {s.atlas}",
                "",
                "**Expected detection signals.** "
                + ", ".join(f"`{x}`" for x in s.expected_signals),
                "",
            ]

    out += [
        "---",
        "",
        "## Simulator coverage",
        "",
        f"All {len(SIMULATORS)} vectors have an executable simulator. "
        "`backend/tests/test_data_pipeline.py` parameterises over the full taxonomy, so a "
        "vector without a working simulator fails the build.",
        "",
        "```bash",
        "# simulate every vector and print a summary",
        ".venv/bin/python -m backend.app.attacks",
        "```",
    ]

    DOCS.mkdir(exist_ok=True)
    (DOCS / "fraud-taxonomy.md").write_text("\n".join(out) + "\n")
    print(f"wrote docs/fraud-taxonomy.md — {len(TAXONOMY)} vectors, {len(by_cat)} categories, "
          f"{len(implemented)}/{len(all_expected)} signals implemented")


if __name__ == "__main__":
    main()
