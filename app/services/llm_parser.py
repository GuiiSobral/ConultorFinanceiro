import json
from typing import Any

import httpx

from app.services.config import get_settings


OLLAMA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "entry_type": {"type": ["string", "null"]},
                    "amount": {"type": ["number", "null"]},
                    "occurred_on": {"type": ["string", "null"]},
                    "category": {"type": ["string", "null"]},
                    "subcategory": {"type": ["string", "null"]},
                    "payment_method": {"type": ["string", "null"]},
                    "description": {"type": ["string", "null"]},
                    "raw_text": {"type": ["string", "null"]},
                    "confidence": {"type": ["number", "null"]}
                },
                "required": [
                    "entry_type",
                    "amount",
                    "occurred_on",
                    "category",
                    "subcategory",
                    "payment_method",
                    "description",
                    "raw_text",
                    "confidence"
                ]
            }
        }
    },
    "required": ["entries"]
}


def build_prompt(message_text: str, captured_at: str) -> str:
    return f"""
Você é um extrator financeiro. Converta a mensagem em uma lista de lançamentos financeiros.

Regras:
- retorne apenas JSON válido
- identifique múltiplos lançamentos quando existirem
- use 'despesa', 'receita' ou 'indefinido' em entry_type
- datas relativas devem considerar captured_at={captured_at}
- category deve ser curta e em minúsculas com underscore quando necessário
- subcategory também deve ser curta
- payment_method deve usar: credito, debito, pix, dinheiro, boleto, transferencia ou null
- confidence deve ser número entre 0 e 1
- quando não souber um campo, use null
- preserve no campo raw_text o trecho correspondente ao lançamento

Mensagem:
{message_text}
""".strip()


async def parse_with_ollama(message_text: str, captured_at: str, submission_id: str) -> list[dict]:
    settings = get_settings()
    payload = {
        "model": settings.ollama_model,
        "prompt": build_prompt(message_text=message_text, captured_at=captured_at),
        "stream": False,
        "format": OLLAMA_SCHEMA,
        "options": {"temperature": 0},
    }

    async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
        response = await client.post(f"{settings.ollama_base_url}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()

    raw_response = data.get("response", "{}")
    parsed = json.loads(raw_response)
    entries = parsed.get("entries", [])

    normalized_entries = []
    for entry in entries:
        normalized_entries.append(
            {
                "submission_id": submission_id,
                "captured_at": captured_at,
                "occurred_on": entry.get("occurred_on"),
                "source_kind": "text",
                "raw_text": entry.get("raw_text") or message_text.strip(),
                "entry_type": entry.get("entry_type") or "indefinido",
                "amount": entry.get("amount"),
                "currency": "BRL",
                "category": entry.get("category") or "a_classificar",
                "subcategory": entry.get("subcategory"),
                "payment_method": entry.get("payment_method"),
                "description": entry.get("description") or entry.get("raw_text") or message_text.strip(),
                "confidence": float(entry.get("confidence") or 0.5),
            }
        )

    return normalized_entries
