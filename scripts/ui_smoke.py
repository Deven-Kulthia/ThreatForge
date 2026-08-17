"""UI smoke test — drives the real dashboard through the judge demo path.

Verifies the end-to-end flow works in a browser, captures screenshots for the writeup,
and fails on console errors. Run with both servers up:

    .venv/bin/uvicorn backend.app.api:app --port 8000 &
    (cd frontend && npm run dev) &
    /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/ui_smoke.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "artifacts" / "screenshots"
BASE = "http://localhost:5173"

TABS = ["Overview", "Red Team", "Live Stream", "Investigate",
        "Fraud Network", "Performance", "Audit Trail"]


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    failures: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        page.goto(BASE)
        page.wait_for_load_state("networkidle")

        # --- boot the environment (skip if the backend is already booted) ---
        boot = page.get_by_role("button", name="Start environment")
        if boot.count() > 0 and boot.is_visible():
            boot.click()
            # Training 25 campaigns takes a few seconds; wait for the live badge.
            page.get_by_text("ENVIRONMENT LIVE").wait_for(timeout=180_000)
        else:
            # Already-running backend: the dashboard should come up live immediately.
            page.get_by_text("ENVIRONMENT LIVE").wait_for(timeout=30_000)
        page.wait_for_timeout(1_200)
        page.screenshot(path=str(SHOTS / "01-overview.png"), full_page=True)

        # --- launch an attack from the red-team panel ---
        page.get_by_role("button", name="Red Team").click()
        page.wait_for_timeout(900)
        page.screenshot(path=str(SHOTS / "02-red-team.png"), full_page=True)

        page.get_by_role("button", name="Launch campaign").click()
        page.get_by_text("Campaign result").wait_for(timeout=120_000)
        page.wait_for_timeout(700)
        page.screenshot(path=str(SHOTS / "03-campaign-result.png"), full_page=True)

        # --- remaining panels ---
        for i, tab in enumerate(TABS[2:], start=4):
            page.get_by_role("button", name=tab).click()
            # The stream panel needs a few seconds of websocket traffic to look alive.
            page.wait_for_timeout(7_000 if tab == "Live Stream" else 1_800)
            slug = tab.lower().replace(" ", "-")
            page.screenshot(path=str(SHOTS / f"{i:02d}-{slug}.png"), full_page=True)

            body = page.inner_text("main")
            if "not initialised" in body:
                failures.append(f"{tab}: environment reported uninitialised")

        # --- explainability must render reason codes ---
        page.get_by_role("button", name="Investigate").click()
        page.wait_for_timeout(2_500)
        if page.get_by_text("Reason codes").count() == 0:
            failures.append("Investigate: no reason codes rendered")

        browser.close()

    # Vite HMR chatter and favicon 404s are noise, not defects.
    real = [e for e in errors
            if "favicon" not in e.lower() and "hmr" not in e.lower()
            and "vite" not in e.lower()]

    for f in failures:
        print(f"FAIL  {f}")
    for e in real[:10]:
        print(f"CONSOLE  {e[:180]}")

    shots = sorted(SHOTS.glob("*.png"))
    print(f"\n{len(shots)} screenshots -> {SHOTS}")
    for s in shots:
        print(f"  {s.name}  {s.stat().st_size // 1024} KB")

    ok = not failures and not real
    print("\nOK  demo path verified end-to-end" if ok else "\nFAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
