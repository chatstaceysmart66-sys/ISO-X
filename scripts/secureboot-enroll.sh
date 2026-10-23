#!/usr/bin/env bash
# ISO-X Secure Boot helper: validate only; never mutates firmware keys.
set -Eeuo pipefail

usage() {
  cat <<'HELP'
ISO-X Secure Boot validation only

Usage:
  scripts/secureboot-enroll.sh MODULE_SIGNING_KEY.pem MODULE_SIGNING_CERT.der|pem

This script does NOT enroll keys, sign bootloaders, enable Secure Boot, or alter UEFI.
It validates that the supplied certificate is parseable and that the private key matches
its public key. MOK enrollment and a complete trusted boot chain are device-specific and
must be performed deliberately on a disposable test device or VM.
HELP
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then usage; exit 0; fi
if [[ $# -ne 2 ]]; then usage >&2; exit 2; fi
KEY="$1"
CERT="$2"
command -v openssl >/dev/null 2>&1 || { echo "ERROR: openssl is required." >&2; exit 3; }
[[ -r "$KEY" && -f "$KEY" ]] || { echo "ERROR: signing key is not a readable regular file." >&2; exit 4; }
[[ -r "$CERT" && -f "$CERT" ]] || { echo "ERROR: certificate is not a readable regular file." >&2; exit 4; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
chmod 700 "$TMP"
if ! openssl pkey -in "$KEY" -pubout -out "$TMP/key-public.pem" >/dev/null 2>&1; then
  echo "ERROR: private key is not a readable OpenSSL private key." >&2; exit 5
fi
if ! openssl x509 -inform DER -in "$CERT" -pubkey -noout -out "$TMP/cert-public.pem" 2>/dev/null; then
  if ! openssl x509 -inform PEM -in "$CERT" -pubkey -noout -out "$TMP/cert-public.pem" 2>/dev/null; then
    echo "ERROR: certificate is neither valid DER nor PEM X.509." >&2; exit 6
  fi
fi
if ! cmp -s <(openssl pkey -pubin -in "$TMP/key-public.pem" -outform DER 2>/dev/null) \
            <(openssl pkey -pubin -in "$TMP/cert-public.pem" -outform DER 2>/dev/null); then
  echo "ERROR: private key and certificate do not match." >&2; exit 7
fi
openssl x509 -inform DER -in "$CERT" -noout -subject -issuer -dates 2>/dev/null || \
  openssl x509 -inform PEM -in "$CERT" -noout -subject -issuer -dates
printf '\nPASS: key/certificate pair matches.\n'
printf 'IMPORTANT: this does not verify UEFI Secure Boot, MOK enrollment, or the trusted boot chain.\n'
