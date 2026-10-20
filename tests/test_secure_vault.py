#!/usr/bin/env python3
"""Integration tests for the local encrypted archive helper; requires OpenSSL."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("secure_vault", ROOT / "scripts/secure-vault.py")
assert spec and spec.loader
vault = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vault)

with tempfile.TemporaryDirectory(prefix="isox-vault-test-") as temporary:
    base = Path(temporary)
    source = base / "source"
    source.mkdir()
    (source / "nested").mkdir()
    (source / "nested" / "hello.txt").write_text("ISO-X local vault test — عربي\n", encoding="utf-8")
    encrypted = base / "source.isoxvault"
    restored_parent = base / "restored"
    vault.encrypt(source, encrypted, b"test-only passphrase")
    assert encrypted.is_file() and encrypted.stat().st_size > 64
    vault.decrypt(encrypted, restored_parent, b"test-only passphrase")
    restored = restored_parent / "source" / "nested" / "hello.txt"
    assert restored.read_text(encoding="utf-8") == "ISO-X local vault test — عربي\n"

    # Wrong passwords and tampering must fail before files are restored.
    wrong_dest = base / "wrong-password"
    try:
        vault.decrypt(encrypted, wrong_dest, b"wrong passphrase")
        raise AssertionError("wrong password was accepted")
    except vault.VaultError:
        pass
    assert not any(wrong_dest.iterdir()) if wrong_dest.exists() else True

    tampered = base / "tampered.isoxvault"
    data = bytearray(encrypted.read_bytes())
    data[len(vault.MAGIC) + vault.SALT_BYTES + 4] ^= 0x01
    tampered.write_bytes(data)
    tamper_dest = base / "tamper-destination"
    try:
        vault.decrypt(tampered, tamper_dest, b"test-only passphrase")
        raise AssertionError("tampered ciphertext was accepted")
    except vault.VaultError:
        pass
    assert not any(tamper_dest.iterdir()) if tamper_dest.exists() else True

print("PASS: vault encrypt/decrypt round-trip, Unicode payload, wrong-password rejection, and tamper rejection")
