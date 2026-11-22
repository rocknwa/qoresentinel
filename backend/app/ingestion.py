"""Data-only Solidity source ingestion; no uploaded code is executed."""
import io
import re
import stat
import zipfile
from pathlib import PurePosixPath
from fastapi import HTTPException
from . import settings

class BadSource(ValueError):
    pass

def safe_path(name: str) -> str:
    if not name or "\\" in name or "\x00" in name or name.startswith("/") or re.match(r"^[a-zA-Z]:", name):
        raise BadSource("Unsafe archive path")
    parts = name.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise BadSource("Unsafe archive path")
    if len(name) > 240 or len(parts) > 16:
        raise BadSource("Archive path too deep or long")
    return str(PurePosixPath(name))

def valid_solidity(source: bytes) -> str:
    if not source or len(source) > settings.MAX_UPLOAD_BYTES:
        raise BadSource("Empty or oversized Solidity file")
    if b"\x00" in source:
        raise BadSource("Binary data is not Solidity source")
    try:
        text = source.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BadSource("Only UTF-8 text is supported") from exc
    if not text.strip():
        raise BadSource("Solidity file is blank")
    return text

def ingest_paste(text: str) -> dict[str, str]:
    return {"Contract.sol": valid_solidity(text.encode("utf-8"))}

def ingest_files(items: list[tuple[str, bytes]]) -> dict[str, str]:
    result = {}
    total = 0
    for name, body in items:
        name = safe_path(name)
        if not name.lower().endswith(".sol"):
            raise BadSource("Only .sol source files are supported")
        if name in result:
            raise BadSource("Duplicate filename")
        total += len(body)
        if total > settings.MAX_TOTAL_BYTES or len(result) >= settings.MAX_FILES:
            raise BadSource("Project file/size limit exceeded")
        result[name] = valid_solidity(body)
    if not result:
        raise BadSource("Project contains no Solidity files")
    return result

def ingest_zip(raw: bytes) -> dict[str, str]:
    if not raw or len(raw) > settings.MAX_ZIP_COMPRESSED_BYTES:
        raise BadSource("ZIP is empty or exceeds compressed-size limit")
    result = {}
    total = 0
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for member in archive.infolist():
                name = member.filename
                # Deny symlinks and non-regular entries; skip normal directories.
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode) or (mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                    raise BadSource("ZIP links and special files are forbidden")
                if member.is_dir():
                    safe_path(name.rstrip("/"))
                    continue
                name = safe_path(name)
                if member.flag_bits & 0x1:
                    raise BadSource("Encrypted ZIP entries are unsupported")
                if member.file_size > settings.MAX_UPLOAD_BYTES:
                    raise BadSource("ZIP entry exceeds file size limit")
                total += member.file_size
                if total > settings.MAX_TOTAL_BYTES:
                    raise BadSource("Expanded ZIP exceeds project size limit")
                if not name.lower().endswith(".sol"):
                    continue  # Ignore config and scripts; never execute them.
                if name in result or len(result) >= settings.MAX_FILES:
                    raise BadSource("Duplicate Solidity path or too many files")
                with archive.open(member) as stream:
                    body = stream.read(settings.MAX_UPLOAD_BYTES + 1)
                if len(body) != member.file_size:
                    raise BadSource("ZIP entry size mismatch")
                result[name] = valid_solidity(body)
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        raise BadSource("Invalid ZIP file") from exc
    if not result:
        raise BadSource("ZIP contains no .sol files")
    return result

def as_http_error(exc: BadSource) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))
