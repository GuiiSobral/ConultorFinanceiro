from app.services.config import get_settings
from app.services.llm_parser import parse_with_ollama
from app.services.parser import parse_text_entries


async def interpret_entries(message_text: str, captured_at: str, submission_id: str) -> list[dict]:
    settings = get_settings()

    if settings.mode == "rules":
        return parse_text_entries(
            message_text=message_text,
            captured_at=captured_at,
            submission_id=submission_id,
        )

    if settings.mode in {"auto", "ai"}:
        try:
            entries = await parse_with_ollama(
                message_text=message_text,
                captured_at=captured_at,
                submission_id=submission_id,
            )
            if entries:
                return entries
        except Exception:
            pass

    return parse_text_entries(
        message_text=message_text,
        captured_at=captured_at,
        submission_id=submission_id,
    )
