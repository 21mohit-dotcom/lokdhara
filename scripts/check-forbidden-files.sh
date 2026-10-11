#!/usr/bin/env bash
# Fails if any tracked file is something Lokdhara must never commit (ADR-017):
# audio, collected-data/export/storage directories, env files, keys, database dumps.
# Used by CI on every push; run locally with: bash scripts/check-forbidden-files.sh
set -euo pipefail

forbidden_path_regex='(^|/)(data|datasets|exports|storage|uploads|recordings|consent|consent-evidence|private|secrets|\.local-storage)/'
forbidden_ext_regex='\.(wav|wave|flac|mp3|ogg|oga|opus|m4a|aac|webm|amr|3gp|3gpp|aif|aiff|wma|caf|mka|sqlite|sqlite3|db|dump|backup|pgdump|pem|key|p12|pfx|parquet)$'
env_regex='(^|/)\.env($|\.)'

status=0
while IFS= read -r -d '' f; do
  lower=$(printf '%s' "$f" | tr '[:upper:]' '[:lower:]')
  if [[ "$lower" =~ $forbidden_path_regex ]]; then echo "FORBIDDEN PATH: $f"; status=1; fi
  if [[ "$lower" =~ $forbidden_ext_regex ]]; then echo "FORBIDDEN FILE TYPE: $f"; status=1; fi
  if [[ "$f" =~ $env_regex ]] && [[ "$(basename "$f")" != ".env.example" ]]; then
    echo "ENV FILE: $f"; status=1
  fi
done < <(git ls-files -z)

if [[ $status -eq 0 ]]; then echo "No forbidden files tracked."; fi
exit $status
