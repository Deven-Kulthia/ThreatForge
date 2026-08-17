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
for m in generator attacks features detect explain; do
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
  ok "$($PY -c "
import json;m=json.load(open('artifacts/metrics.json'))
d=m['discrimination'];l=m['latency']
print(f\"PR-AUC {d['pr_auc']:.4f} · decision p99 {l['decision_p99_ms']}ms · zero-day {m['zero_day']['unseen_recall']:.3f}\")")"
else
  bad "artifacts/metrics.json missing — run: $PY -m backend.app.evaluate"
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
