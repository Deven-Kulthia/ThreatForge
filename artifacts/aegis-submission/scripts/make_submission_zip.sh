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
rm -f "$OUT"

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
     "artifacts/aegis-submission.zip"

# Fail loudly rather than ship a credential. Matches a bare `.env` entry only —
# `.env.example` is intentionally included as setup documentation.
if unzip -l "$OUT" | grep -qE '[[:space:]]\.env$'; then
  echo "ABORT: .env is inside $OUT — a credential would ship to judges." >&2
  rm -f "$OUT"
  exit 1
fi
for pat in '\.venv/' 'node_modules/'; do
  if unzip -l "$OUT" | grep -qE "$pat"; then
    echo "ABORT: $pat leaked into $OUT." >&2
    rm -f "$OUT"
    exit 1
  fi
done

FILES=$(unzip -l "$OUT" | tail -1 | awk '{print $2}')
echo "OK  $OUT · $FILES files · $(du -h "$OUT" | cut -f1) · no credentials, no vendored deps"
