#!/usr/bin/env bash
set -Eeuo pipefail
if [[ -r /usr/share/iso-x/secure-vault.py ]]; then
  exec python3 /usr/share/iso-x/secure-vault.py "$@"
fi
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$PROJECT_DIR/scripts/secure-vault.py" "$@"
