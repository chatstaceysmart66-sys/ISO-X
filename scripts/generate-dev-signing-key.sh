#!/usr/bin/env bash
set -euo pipefail
# Development/release provisioning helper. Keep private keys outside the repository.
OUT="${1:-$HOME/.local/share/isox-signing}"
umask 077
mkdir -p "$OUT"
chmod 700 "$OUT"
if [[ -e "$OUT/isox-release.key" ]]; then
  echo "Refusing to overwrite existing key: $OUT/isox-release.key" >&2
  exit 2
fi
openssl req -new -x509 -newkey rsa:3072 -sha256 -nodes -days 3650 \
  -subj "/CN=ISO-X Release Signing/O=ISO-X/C=IQ" \
  -keyout "$OUT/isox-release.key" -out "$OUT/isox-release.crt"
chmod 600 "$OUT/isox-release.key"
chmod 644 "$OUT/isox-release.crt"
echo "Created private signing key outside the source tree: $OUT/isox-release.key"
echo "BACK UP SECURELY. Do not put the private key in the ISO or source ZIP."
echo "This creates an OpenSSL signing identity; it does not automatically enroll a kernel MOK or enable Secure Boot."
