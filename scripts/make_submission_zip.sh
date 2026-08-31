#!/usr/bin/env bash
# Build the code archive to attach to the Kaggle writeup.
#
# Judges cannot open a private GitHub repo, so artifact 1 ("a complete, runnable
# code repository") travels as a zip. This script exists because the obvious
# `zip -r` shipped a real .env containing a GitHub Personal Access Token — an
# exclusion list belongs in version control, not in someone's shell history.
#
#   ./scripts/make_submission_zip.sh   ->  artifacts/aegis-submission.zip

set -euo pipefail
cd "$(dirname "$0")/.."

OUT=artifacts/aegis-submission.zip
HIST=GIT-HISTORY.txt
rm -f "$OUT"

# The archive excludes .git/, so commit history — the evidence that this was built
# iteratively rather than dumped at the deadline — would be lost. Ship it as text.
{
  echo "Aegis — commit history"
  echo "Repository: github.com/Deven-Kulthia/ThreatForge (public, per Step 4 of the"
  echo "host submission guidelines)"
  echo "Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo
  echo "=== Summary ==="
  echo "commits: $(git rev-list --count HEAD)"
  echo "files tracked: $(git ls-files | wc -l | tr -d ' ')"
  echo
  echo "=== Full log with messages ==="
  git log --stat --date=iso --format='%n----------%ncommit %h%nDate:   %ad%n%n%B'
} > "$HIST"

zip -qr "$OUT" . \
  -x ".venv/*" \
     "frontend/node_modules/*" \
     "frontend/dist/*" \
     ".git/*" \
     ".env" \
     ".firecrawl/*" \
     ".pytest_cache/*" \
     "**/__pycache__/*" \
     "**/.DS_Store" \
     "research/*.html" \
     "artifacts/aegis-submission.zip" \
     "artifacts/aegis-submission/*" \
     "artifacts/aegis-project-explained.html"

rm -f "$HIST"

# Fail loudly rather than ship a credential. Matches a bare `.env` entry only —
# `.env.example` is intentionally included as setup documentation.
if unzip -l "$OUT" | grep -qE '[[:space:]]\.env$'; then
  echo "ABORT: .env is inside $OUT — a credential would ship to judges." >&2
  rm -f "$OUT"
  exit 1
fi
for pat in '\.venv/' 'node_modules/' 'aegis-submission/'; do
  if unzip -l "$OUT" | grep -qE "$pat"; then
    echo "ABORT: $pat leaked into $OUT." >&2
    rm -f "$OUT"
    exit 1
  fi
done

FILES=$(unzip -l "$OUT" | tail -1 | awk '{print $2}')
echo "OK  $OUT · $FILES files · $(du -h "$OUT" | cut -f1) · no credentials, no vendored deps"
