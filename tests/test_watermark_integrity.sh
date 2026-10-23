#!/usr/bin/env bash
set -euo pipefail
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
openssl req -new -x509 -newkey rsa:2048 -nodes -days 1 -subj '/CN=ISO-X test only' -keyout "$TMP/key.pem" -out "$TMP/cert.pem" >/dev/null 2>&1
openssl x509 -in "$TMP/cert.pem" -pubkey -noout > "$TMP/public.pem"
printf 'pretend signed module payload\n' > "$TMP/isox_watermark.ko"
openssl dgst -sha256 -sign "$TMP/key.pem" -out "$TMP/isox_watermark.ko.sig" "$TMP/isox_watermark.ko"
openssl dgst -sha256 -verify "$TMP/public.pem" -signature "$TMP/isox_watermark.ko.sig" "$TMP/isox_watermark.ko" >/dev/null
printf 'tampered\n' >> "$TMP/isox_watermark.ko"
if openssl dgst -sha256 -verify "$TMP/public.pem" -signature "$TMP/isox_watermark.ko.sig" "$TMP/isox_watermark.ko" >/dev/null 2>&1; then
  echo "FAIL: tampering was not detected" >&2; exit 1
fi
echo "PASS: detached signature verifies original module payload and rejects modified payload (test fixture only)"
