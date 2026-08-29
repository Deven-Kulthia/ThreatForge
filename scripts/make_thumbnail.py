"""Render the 560x280 card/thumbnail image for the Kaggle writeup.

Kaggle shows this card in listings, so it is the first thing a judge sees. Uses
the same Playwright Chromium as the browser smoke test and the PDF builder —
no new dependency, no image-editing toolchain.

Numbers come from artifacts/metrics.json so the card cannot quote stale figures.

    /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/make_thumbnail.py

Output: artifacts/aegis-card-560x280.png
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "artifacts" / "metrics.json"
OUT = ROOT / "artifacts" / "aegis-card-560x280.png"
TMP = ROOT / "artifacts" / ".card.html"

W, H = 560, 280


def html(m: dict) -> str:
    di, lat, zd = m["discrimination"], m["latency"], m["zero_day"]
    d = m["dataset"]
    return f"""<!doctype html><meta charset="utf-8"><style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:{W}px; height:{H}px; background:#070B14; overflow:hidden;
         font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; color:#E6EDF7; }}
  .wrap {{ padding:24px 26px; height:100%; display:flex; flex-direction:column; }}
  .dots {{ display:flex; align-items:center; margin-bottom:14px; }}
  .dot {{ width:22px; height:22px; border-radius:50%; }}
  .r {{ background:#EB001B; }} .a {{ background:#F79E1B; margin-left:-8px; }}
  .brand {{ margin-left:11px; font-size:13px; letter-spacing:.16em;
            text-transform:uppercase; color:#8A99AD; font-weight:700; }}
  h1 {{ font-size:35px; font-weight:700; letter-spacing:-.9px; line-height:1; }}
  .tag {{ margin-top:9px; font-size:13.5px; color:#8A99AD; line-height:1.35; }}
  .red {{ color:#F1554F; font-weight:700; }} .blue {{ color:#60A5FA; font-weight:700; }}
  .row {{ margin-top:auto; display:flex; gap:9px; }}
  .m {{ flex:1; background:#10172699; border:1px solid #1E293B; border-radius:7px;
        padding:8px 9px; }}
  .k {{ font-size:8px; letter-spacing:.1em; text-transform:uppercase; color:#8A99AD;
        font-weight:700; }}
  .v {{ font-size:19px; font-weight:700; margin-top:2px; line-height:1; }}
  .g {{ color:#34D399; }} .b {{ color:#60A5FA; }} .p {{ color:#A78BFA; }}
  .foot {{ margin-top:10px; font-size:9.5px; color:#5A687A; }}
</style>
<div class="wrap">
  <div class="dots">
    <div class="dot r"></div><div class="dot a"></div>
    <div class="brand">Mastercard Innovation Challenge 2026</div>
  </div>
  <h1>Aegis</h1>
  <div class="tag">AI Defence Lab for Payment Security &nbsp;·&nbsp; closed-loop
    <span class="red">red team</span> / <span class="blue">blue team</span><br>
    {d['attack_vectors']} GenAI-era attack vectors &nbsp;·&nbsp; identify → generate → defend</div>
  <div class="row">
    <div class="m"><div class="k">PR-AUC</div>
      <div class="v g">{di['pr_auc']:.3f}</div></div>
    <div class="m"><div class="k">Decision p99</div>
      <div class="v b">{lat['decision_p99_ms']:.1f}ms</div></div>
    <div class="m"><div class="k">Zero-day recall</div>
      <div class="v p">{zd['unseen_recall']:.3f}</div></div>
  </div>
  <div class="foot">100% synthetic data · simulator network-isolated by construction</div>
</div>"""


def main() -> None:
    m = json.loads(METRICS.read_text())
    TMP.write_text(html(m))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        pg.goto(TMP.as_uri())
        pg.wait_for_load_state("networkidle")
        pg.screenshot(path=str(OUT))
        b.close()
    TMP.unlink(missing_ok=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB, {W}x{H} @2x)")


if __name__ == "__main__":
    main()
