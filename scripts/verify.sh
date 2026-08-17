#!/usr/bin/env bash
# Pre-push verification gate. Nothing is pushed unless this exits 0.
#
#   ./scripts/verify.sh            backend only (fast, ~2 min)
#   ./scripts/verify.sh --full     also frontend typecheck + build + browser smoke
#
# The browser smoke stage needs both servers running; it is skipped with a clear
# message rather than failing the gate if they are not up, because a missing dev
# server is an environment condition, not a defect in the code being pushed.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

PY=.venv/bin/python
FAIL=0
FULL=0
[ "${1:-}" = "--full" ] && FULL=1

step() { printf '\n\033[1m▶ %s\033[0m\n' "$1"; }
ok()   { printf '\033[32m  ✓ %s\033[0m\n' "$1"; }
bad()  { printf '\033[31m  ✗ %s\033[0m\n' "$1"; FAIL=1; }

run() { # run <label> <command...>
  local label="$1"; shift
  if out=$("$@" 2>&1); then
    ok "$label${out:+ — $(printf '%s' "$out" | tail -1)}"
  else
    bad "$label"
    printf '%s\n' "$out" | tail -15 | sed 's/^/      /'
  fi
}

step "Module self-checks"
for m in generator attacks features fidelity detect explain; do
  run "$m" $PY -m backend.app.$m
done

step "Test suite"
if out=$($PY -m pytest backend/tests -q --no-header -p no:warnings 2>&1); then
  ok "pytest — $(printf '%s' "$out" | grep -E '^[0-9]+ passed' | tail -1)"
else
  bad "pytest"
  printf '%s\n' "$out" | grep -E 'FAILED|ERROR|assert' | head -15 | sed 's/^/      /'
fi

step "Secrets and compliance"
if git diff --cached --name-only 2>/dev/null | grep -qE '(^|/)\.env$'; then
  bad ".env is staged — ABORT"
else
  ok ".env not staged"
fi
if git ls-files 2>/dev/null | grep -qE 'research/.*\.html$|kaggle-raw/'; then
  bad "competition page captures are tracked (Rules §5 IP)"
else
  ok "no competition captures tracked"
fi
if git ls-files 2>/dev/null | grep -qE 'node_modules/|\.venv/|\.tsbuildinfo$'; then
  bad "build artifacts or dependencies are tracked"
else
  ok "no build artifacts tracked"
fi
if grep -rlE 'ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}' \
     --include='*.py' --include='*.ts' --include='*.tsx' --include='*.md' . \
     2>/dev/null | grep -v '\.venv/' | grep -q .; then
  bad "possible credential in tracked source"
else
  ok "no credentials in source"
fi

step "Metrics artifact"
if [ -f artifacts/metrics.json ]; then
  # Staleness guard. Metrics generated BEFORE a change to the data or model pipeline
  # are silently wrong, and every published figure inherits the error. Caught once
  # already: metrics from 20:51 were quoted after a 22:16 pipeline fix.
  STALE=$(find backend/app -name '*.py' -newer artifacts/metrics.json 2>/dev/null)
  if [ -n "$STALE" ]; then
    bad "metrics.json is STALE — these changed after it was generated:
$(echo "$STALE" | sed 's/^/        /')
      regenerate: $PY -m backend.app.evaluate"
  else
    ok "fresh (no backend source newer than metrics.json)"
  fi
  ok "$($PY -c "
import json;m=json.load(open('artifacts/metrics.json'))
d=m['discrimination'];l=m['latency']
print(f\"PR-AUC {d['pr_auc']:.4f} · decision p99 {l['decision_p99_ms']}ms · zero-day {m['zero_day']['unseen_recall']:.3f}\")")"
  ok "$($PY -c "
import json;m=json.load(open('artifacts/metrics.json'))
f=m.get('fidelity');print('fidelity — '+f['summary'] if f else 'fidelity section MISSING')")"
else
  bad "artifacts/metrics.json missing — run: $PY -m backend.app.evaluate"
fi

# Prose-drift guard. Hand-written docs quote headline figures; when metrics are
# regenerated those quotes go stale silently. Caught once already: the whole doc set
# quoted a PR-AUC from pre-fix code. Compare every quoted PR-AUC / p99 against the
# artifact and fail on disagreement.
step "Docs agree with metrics"
if [ -f artifacts/metrics.json ]; then
  DRIFT=$($PY - <<'PYEOF'
import json, re, pathlib
m = json.load(open("artifacts/metrics.json"))
want = {
    "PR-AUC": f"{m['discrimination']['pr_auc']:.3f}",
    "p99": f"{m['latency']['decision_p99_ms']:.1f}",
}
pats = {
    "PR-AUC": re.compile(r"PR-AUC[^\d\n]{0,24}(\d\.\d{3})"),
    "p99": re.compile(r"p99[^\d\n]{0,12}(\d{1,3}\.\d)\s?ms"),
}
bad = []
for f in ("README.md", "docs/current-state.md", "docs/submission-writeup.md",
          "docs/presenter-guide.md", "docs/architecture.md", "docs/demo-flow.md"):
    p = pathlib.Path(f)
    if not p.exists():
        continue
    for i, line in enumerate(p.read_text().splitlines(), 1):
        for key, rx in pats.items():
            for got in rx.findall(line):
                if got != want[key]:
                    bad.append(f"{f}:{i} quotes {key} {got}, metrics say {want[key]}")
print("\n".join(bad))
PYEOF
)
  if [ -n "$DRIFT" ]; then
    bad "docs quote figures that disagree with metrics.json:
$(echo "$DRIFT" | sed 's/^/        /')"
  else
    ok "quoted PR-AUC and p99 match metrics.json"
  fi
fi

if [ "$FULL" = "1" ]; then
  step "Frontend typecheck and build"
  if [ -d frontend/node_modules ]; then
    (cd frontend && run "tsc" ./node_modules/.bin/tsc --noEmit)
    (cd frontend && run "vite build" npm run build --silent)
  else
    bad "frontend/node_modules missing — run: (cd frontend && npm install)"
  fi

  step "Browser smoke test"
  if curl -sf -o /dev/null http://127.0.0.1:8000/api/health \
     && curl -sf -o /dev/null http://localhost:5173/; then
    run "playwright demo path" \
      /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 scripts/ui_smoke.py
  else
    printf '  \033[33m⊘ skipped — servers not running\033[0m\n'
    printf '      start them with:\n'
    printf '      %s -m uvicorn backend.app.api:app --port 8000 &\n' "$PY"
    printf '      (cd frontend && npm run dev) &\n'
  fi
fi

if [ "$FAIL" = "0" ]; then
  printf '\n\033[32m\033[1mVERIFIED — safe to push\033[0m\n'
else
  printf '\n\033[31m\033[1mFAILED — do not push\033[0m\n'
fi
exit $FAIL
