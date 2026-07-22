param(
  [string]$Repository = "matteodante/therapist"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  throw "GitHub CLI (gh) is required: https://cli.github.com/"
}

gh auth status

if (-not (Test-Path ".git")) {
  git init -b main
}

git add .
$staged = git diff --cached --name-only
if ($staged) {
  git commit -m "Initialize Therapist with Flue"
}

gh repo create $Repository `
  --public `
  --description "Open-source, self-hosted therapy agent built with Flue" `
  --source . `
  --remote origin `
  --push
