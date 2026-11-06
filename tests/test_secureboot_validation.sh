#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/scripts/secureboot-enroll.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
chmod 700 "$TMP"
openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 2 \
  -subj '/CN=ISO-X test signing/O=ISO-X test' \
  -keyout "$TMP/key.pem" -out "$TMP/cert.pem" >/dev/null 2>&1
openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 2 \
  -subj '/CN=ISO-X wrong test signing/O=ISO-X test' \
  -keyout "$TMP/wrong-key.pem" -out "$TMP/wrong-cert.pem" >/dev/null 2>&1
"$SCRIPT" "$TMP/key.pem" "$TMP/cert.pem" >"$TMP/match.out"
grep -q 'PASS: key/certificate pair matches' "$TMP/match.out"
if "$SCRIPT" "$TMP/key.pem" "$TMP/wrong-cert.pem" >"$TMP/mismatch.out" 2>&1; then
  echo 'FAIL: mismatched key/certificate was accepted' >&2; exit 1
fi
if "$SCRIPT" "$TMP/key.pem" "$TMP/wrong-key.pem" >"$TMP/mismatch2.out" 2>&1; then
  echo 'FAIL: mismatched private key/certificate was accepted' >&2; exit 1
fi
printf 'not a certificate\n' > "$TMP/invalid.cert"
if "$SCRIPT" "$TMP/key.pem" "$TMP/invalid.cert" >"$TMP/invalid.out" 2>&1; then
  echo 'FAIL: invalid certificate was accepted' >&2; exit 1
fi
grep -q 'does NOT enroll keys' < <("$SCRIPT" --help)
printf 'PASS: Secure Boot helper validates matching key/cert only, rejects mismatches, and never enrolls UEFI keys.\n'
