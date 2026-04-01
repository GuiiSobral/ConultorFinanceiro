import json
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.services.interpreter import interpret_entries

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
INBOX_DIR = DATA_DIR / "inbox"
SUBMISSIONS_DIR = DATA_DIR / "submissions"

ALLOWED_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".wav",
    ".mp3",
    ".m4a",
    ".ogg",
    ".webm",
}


def slugify_filename(filename: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]+", "-", filename.strip().lower())
    sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
    return sanitized or "arquivo"


async def save_submission(message_text: str, files: list[UploadFile]) -> dict:
    timestamp = datetime.now()
    submission_id = f"{timestamp.strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"

    inbox_dir = INBOX_DIR / timestamp.strftime("%Y/%m/%d") / submission_id
    inbox_dir.mkdir(parents=True, exist_ok=True)
    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)

    saved_files = []

    for index, upload in enumerate(files, start=1):
        original_name = (upload.filename or "arquivo-sem-nome").strip()
        suffix = Path(original_name).suffix.lower()

        if suffix and suffix not in ALLOWED_SUFFIXES:
            raise ValueError(
                f"Formato não suportado: {suffix}. Use áudio, imagem ou PDF."
            )

        safe_stem = slugify_filename(Path(original_name).stem)
        safe_name = f"{index:02d}_{safe_stem}{suffix}"
        target_path = inbox_dir / safe_name

        content = await upload.read()
        target_path.write_bytes(content)

        saved_files.append(
            {
                "original_name": original_name,
                "stored_path": str(target_path.relative_to(BASE_DIR)),
                "content_type": upload.content_type,
                "size_bytes": len(content),
            }
        )

    metadata = {
        "submission_id": submission_id,
        "captured_at": timestamp.isoformat(timespec="seconds"),
        "message_text": message_text.strip(),
        "saved_files": saved_files,
    }

    metadata_path = SUBMISSIONS_DIR / f"{submission_id}.json"
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return metadata


async def register_submission(message_text: str, files: list[UploadFile]) -> dict:
    metadata = await save_submission(message_text=message_text, files=files)
    parsed_entries = await interpret_entries(
        message_text=metadata.get("message_text", ""),
        captured_at=metadata["captured_at"],
        submission_id=metadata["submission_id"],
    )

    metadata["parsed_entries"] = parsed_entries
    metadata["parsed_entry"] = parsed_entries[0] if parsed_entries else None
    return metadata
