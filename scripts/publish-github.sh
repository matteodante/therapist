#!/usr/bin/env bash
set -euo pipefail

REPO="${1:-matteodante/therapist}"

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required: https://cli.github.com/" >&2
  exit 1
fi

gh auth status

if [[ ! -d .git ]]; then
  git init -b main
fi

git add .
if ! git diff --cached --quiet; then
  git commit -m "Initialize Therapist with Flue"
fi

gh repo create "$REPO" \
  --public \
  --description "Open-source, self-hosted therapy agent built with Flue" \
  --source . \
  --remote origin \
  --push
