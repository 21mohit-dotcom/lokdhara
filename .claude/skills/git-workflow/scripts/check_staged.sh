#!/usr/bin/env bash
# Fails if staged changes include files Lokdhara must never commit.
# Usage: bash .claude/skills/git-workflow/scripts/check_staged.sh
set -euo pipefail

status=0
staged=$(git diff --cached --name-only --diff-filter=ACMR)

if [ -z "$staged" ]; then
  echo "No staged files."
  exit 0
fi

forbidden_path_regex='(^|/)(data|datasets|exports|storage|uploads|recordings|consent|consent-evidence|private|secrets|\.local-storage)/'
forbidden_ext_regex='\.(wav|wave|flac|mp3|ogg|oga|opus|m4a|aac|webm|amr|3gp|3gpp|aif|aiff|wma|caf|mka|sqlite|sqlite3|db|dump|backup|pgdump|pem|key|p12|pfx|parquet)$'
env_regex='(^|/)\.env($|\.)'

while IFS= read -r f; do
  lower=$(printf '%s' "$f" | tr '[:upper:]' '[:lower:]')
  if printf '%s' "$lower" | grep -Eq "$forbidden_path_regex"; then
    echo "FORBIDDEN PATH: $f"; status=1
  fi
  if printf '%s' "$lower" | grep -Eq "$forbidden_ext_regex"; then
    echo "FORBIDDEN FILE TYPE: $f"; status=1
  fi
  if printf '%s' "$f" | grep -Eq "$env_regex" && [ "$(basename "$f")" != ".env.example" ]; then
    echo "ENV FILE: $f"; status=1
  fi
done <<< "$staged"

# Common secret patterns in staged content (added lines only).
secret_regex='(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})'
if git diff --cached -U0 | grep -E '^\+' | grep -Eq "$secret_regex"; then
  echo "POSSIBLE SECRET in staged changes:"
  git diff --cached -U0 | grep -E '^\+' | grep -En "$secret_regex" | cut -c1-120
  status=1
fi

# Large files are suspicious in a code+docs repository.
while IFS= read -r f; do
  if [ -f "$f" ] && [ "$(wc -c < "$f")" -gt 1048576 ]; then
    echo "LARGE FILE (>1 MB), check it is not data: $f"; status=1
  fi
done <<< "$staged"

if [ "$status" -eq 0 ]; then
  echo "Staged files OK ($(printf '%s\n' "$staged" | wc -l) files)."
fi
exit "$status"
