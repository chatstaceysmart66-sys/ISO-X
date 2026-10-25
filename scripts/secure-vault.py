#!/usr/bin/env python3
"""ISO-X password vault wrapper: OpenSSL AES-256-CBC + PBKDF2 + HMAC-SHA256.

The HMAC is checked before decryption. Passphrases are read from a TTY and
passed to OpenSSL through an inherited file descriptor, not as command args.
This is a general-purpose archive helper, not a kernel or boot-chain security layer.
"""
from __future__ import annotations
import getpass
import hashlib
import hmac
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import tempfile

MAGIC = b"ISOXVAULT1"
SALT_BYTES = 16
TAG_BYTES = 32
PBKDF2_ROUNDS = 600_000
CHUNK = 1024 * 1024

class VaultError(RuntimeError):
    pass

def ask_secret(confirm: bool = False) -> bytes:
    first = getpass.getpass("كلمة مرور الخزنة: ")
    if not first:
        raise VaultError("كلمة المرور فارغة؛ أُلغيت العملية.")
    if confirm:
        second = getpass.getpass("أعد كلمة المرور للتأكيد: ")
        if first != second:
            raise VaultError("كلمتا المرور غير متطابقتين.")
    return first.encode("utf-8")

def run_openssl(mode: str, src_path: Path, dst_path: Path, secret: bytes) -> None:
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, secret + b"\n")
    finally:
        os.close(write_fd)
    command = [
        "openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", str(PBKDF2_ROUNDS),
        "-md", "sha256", "-salt", "-pass", f"fd:{read_fd}",
    ]
    command.insert(2, "-d") if mode == "dec" else None
    try:
        with src_path.open("rb") as source, dst_path.open("wb") as target:
            completed = subprocess.run(command, stdin=source, stdout=target, stderr=subprocess.PIPE,
                                       pass_fds=(read_fd,), check=False)
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise VaultError(f"فشل OpenSSL: {detail or 'سبب غير محدد'}")
    finally:
        os.close(read_fd)

def safe_tar_extract(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    seen: set[str] = set()
    with tarfile.open(archive_path, mode="r:") as archive:
        members = archive.getmembers()
        for member in members:
            rel = PurePosixPath(member.name)
            if rel.is_absolute() or not rel.parts or any(part in ("", ".", "..") for part in rel.parts):
                raise VaultError(f"مسار غير آمن داخل الأرشيف: {member.name!r}")
            if member.name in seen:
                raise VaultError(f"مسار مكرر داخل الأرشيف: {member.name!r}")
            seen.add(member.name)
            if not (member.isdir() or member.isfile()):
                raise VaultError(f"نوع ملف غير مسموح داخل الأرشيف: {member.name!r}")
            target = (root / Path(*rel.parts)).resolve()
            if target != root and root not in target.parents:
                raise VaultError(f"المسار يخرج من مجلد الوجهة: {member.name!r}")
        for member in members:
            rel = PurePosixPath(member.name)
            target = root / Path(*rel.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True, mode=0o755)
                continue
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            if target.exists():
                raise VaultError(f"سيتم رفض الكتابة فوق ملف موجود: {target}")
            extracted = archive.extractfile(member)
            if extracted is None:
                raise VaultError(f"تعذر قراءة عضو الأرشيف: {member.name}")
            with extracted, target.open("xb") as output:
                shutil.copyfileobj(extracted, output, length=CHUNK)
            target.chmod(0o600 if member.mode & 0o077 == 0 else (member.mode & 0o755))

def encrypt(source: Path, output: Path, secret: bytes) -> None:
    if source.is_symlink():
        raise VaultError("مصدر التشفير لا يجوز أن يكون رابطًا رمزيًا.")
    source = source.resolve()
    if not source.is_dir():
        raise VaultError("مصدر التشفير يجب أن يكون مجلدًا عاديًا وليس رابطًا رمزيًا.")
    output = output.resolve()
    if output == source or source in output.parents:
        raise VaultError("ملف الخزنة لا يجوز أن يكون داخل المجلد المصدر.")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise VaultError(f"يرفض استبدال ملف موجود: {output}")
    with tempfile.TemporaryDirectory(prefix="isox-vault-", dir=output.parent) as tmpdir:
        tmp = Path(tmpdir)
        archive_path, encrypted_path = tmp / "archive.tar", tmp / "cipher.bin"
        with tarfile.open(archive_path, mode="w", format=tarfile.PAX_FORMAT) as archive:
            archive.add(source, arcname=source.name, recursive=True)
        with tarfile.open(archive_path, mode="r:") as archive:
            bad = [m.name for m in archive.getmembers() if not (m.isdir() or m.isfile())]
        if bad:
            raise VaultError(f"المصدر يحتوي روابط أو أنواع ملفات غير مسموحة: {bad[0]}")
        run_openssl("enc", archive_path, encrypted_path, secret)
        mac_salt = os.urandom(SALT_BYTES)
        mac_key = hashlib.pbkdf2_hmac("sha256", secret, mac_salt, PBKDF2_ROUNDS, dklen=32)
        header = MAGIC + mac_salt
        signer = hmac.new(mac_key, digestmod=hashlib.sha256)
        signer.update(header)
        temp_output = output.with_name(output.name + ".part")
        try:
            with temp_output.open("xb") as target, encrypted_path.open("rb") as encrypted:
                target.write(header)
                while chunk := encrypted.read(CHUNK):
                    signer.update(chunk)
                    target.write(chunk)
                target.write(signer.digest())
                target.flush(); os.fsync(target.fileno())
            os.replace(temp_output, output)
            output.chmod(0o600)
        finally:
            temp_output.unlink(missing_ok=True)

def decrypt(source: Path, destination: Path, secret: bytes) -> None:
    source = source.resolve()
    if not source.is_file():
        raise VaultError("ملف الخزنة غير موجود.")
    if destination.is_symlink():
        raise VaultError("مجلد الاستعادة لا يجوز أن يكون رابطًا رمزيًا.")
    if destination.exists() and any(destination.iterdir() if destination.is_dir() else [destination]):
        raise VaultError("مجلد الوجهة موجود وغير فارغ؛ لن تُستبدل أي ملفات.")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="isox-vault-", dir=destination.parent) as tmpdir:
        tmp = Path(tmpdir)
        cipher_path, archive_path = tmp / "cipher.bin", tmp / "archive.tar"
        file_size = source.stat().st_size
        header_size = len(MAGIC) + SALT_BYTES
        if file_size < header_size + TAG_BYTES + 32:
            raise VaultError("ملف الخزنة أقصر من صيغة الحاوية الصحيحة.")
        with source.open("rb") as incoming:
            header = incoming.read(header_size)
            if not header.startswith(MAGIC):
                raise VaultError("صيغة الخزنة غير معروفة.")
            mac_salt = header[len(MAGIC):]
            data_size = file_size - header_size - TAG_BYTES
            mac_key = hashlib.pbkdf2_hmac("sha256", secret, mac_salt, PBKDF2_ROUNDS, dklen=32)
            signer = hmac.new(mac_key, digestmod=hashlib.sha256)
            signer.update(header)
            remaining = data_size
            with cipher_path.open("wb") as cipher:
                while remaining:
                    chunk = incoming.read(min(CHUNK, remaining))
                    if not chunk:
                        raise VaultError("نهاية ملف غير متوقعة.")
                    signer.update(chunk); cipher.write(chunk); remaining -= len(chunk)
            tag = incoming.read(TAG_BYTES)
            if len(tag) != TAG_BYTES or incoming.read(1):
                raise VaultError("طول ملف الخزنة غير صحيح.")
        if not hmac.compare_digest(signer.digest(), tag):
            raise VaultError("فشل التحقق HMAC: كلمة المرور خاطئة أو الملف معدّل.")
        run_openssl("dec", cipher_path, archive_path, secret)
        try:
            safe_tar_extract(archive_path, destination)
        except Exception:
            # Do not leave a partial restore after a malformed archive.
            shutil.rmtree(destination, ignore_errors=True)
            raise

def prompt_vault_arguments(read=input, write=print) -> tuple[str, str, str]:
    write("1) تشفير مجلد إلى ملف خزنة")
    write("2) استعادة ملف خزنة إلى مجلد")
    choice = read("اختر 1 أو 2: ").strip().lower()
    if choice in ("1", "enc", "encrypt", "تشفير"):
        mode = "enc"
        first_prompt = "مسار المجلد المراد تشفيره: "
        second_prompt = "مسار ملف الخزنة الناتج: "
    elif choice in ("2", "dec", "decrypt", "استعادة"):
        mode = "dec"
        first_prompt = "مسار ملف الخزنة: "
        second_prompt = "مسار مجلد الاستعادة: "
    else:
        raise VaultError("اختيار غير صالح؛ أُلغيت العملية.")

    first = read(first_prompt)
    second = read(second_prompt)
    if not first.strip() or not second.strip():
        raise VaultError("المسارات مطلوبة؛ أُلغيت العملية.")
    return mode, first, second


def main(argv: list[str]) -> int:
    if len(argv) == 1:
        if not sys.stdin.isatty():
            print("الاستخدام: secure-vault.sh enc <مجلد_المصدر> <ملف.enc>\n"
                  "        secure-vault.sh dec <ملف.enc> <مجلد_الاستعادة>", file=sys.stderr)
            return 2
        try:
            mode, first, second = prompt_vault_arguments()
        except (EOFError, KeyboardInterrupt):
            print("أُلغيت العملية.", file=sys.stderr)
            return 1
        except VaultError as exc:
            print(f"خطأ: {exc}", file=sys.stderr)
            return 1
    elif len(argv) == 4 and argv[1] in ("enc", "dec"):
        mode = argv[1]
        first, second = argv[2], argv[3]
    else:
        print("الاستخدام: secure-vault.sh enc <مجلد_المصدر> <ملف.enc>\n"
              "        secure-vault.sh dec <ملف.enc> <مجلد_الاستعادة>", file=sys.stderr)
        return 2

    first_path, second_path = Path(first), Path(second)
    try:
        secret = ask_secret(confirm=(mode == "enc"))
        if mode == "enc":
            encrypt(first_path, second_path, secret)
            print(f"تم إنشاء ملف مشفّر ومتحقق من سلامته: {second_path}")
        else:
            decrypt(first_path, second_path, secret)
            print(f"تم فك الأرشيف بعد التحقق من سلامته: {second_path}")
        return 0
    except (VaultError, OSError, tarfile.TarError, subprocess.SubprocessError) as exc:
        print(f"خطأ: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
