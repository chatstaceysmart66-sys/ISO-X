#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$#" -ne 1 ]]; then
  echo "Usage: $0 NONCE_FILE" >&2
  exit 2
fi

nonce="$(cat -- "$1")"
if [[ ! "$nonce" =~ ^[a-f0-9]{32}$ ]]; then
  echo "CI nonce file must contain exactly 32 lowercase hexadecimal characters with no prefix." >&2
  exit 1
fi

printf '%s\n' "$nonce"
