from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.services.database import cancel_entry, confirm_entry, init_db, list_entries, update_entry
from app.services.storage import register_submission

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_FILE = BASE_DIR / "templates" / "index.html"

app = FastAPI(title="Consultor Financeiro Local")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


class EntryPayload(BaseModel):
    submission_id: str
    captured_at: str
    occurred_on: str | None = None
    raw_text: str | None = None
    entry_type: str | None = None
    amount: float | None = None
    currency: str = "BRL"
    category: str | None = None
    subcategory: str | None = None
    payment_method: str | None = None
    description: str | None = None
    confidence: float = 0


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_FILE)


@app.post("/api/submit")
async def submit_entry(
    message_text: str = Form(default=""),
    files: list[UploadFile] | None = File(default=None),
):
    if not message_text.strip() and not files:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "message": "Envie um texto, áudio, imagem ou PDF antes de salvar.",
            },
        )

    try:
        result = await register_submission(
            message_text=message_text,
            files=files or [],
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "message": str(exc)},
        )

    return {
        "ok": True,
        "submission_id": result["submission_id"],
        "saved_files": result["saved_files"],
        "parsed_entry": result.get("parsed_entry"),
        "parsed_entries": result.get("parsed_entries", []),
        "message": "Entrada recebida. Revise e confirme antes de salvar.",
    }


@app.post("/api/confirm")
async def confirm_entry_route(payload: EntryPayload):
    entry_id = confirm_entry(payload.model_dump())
    return {
        "ok": True,
        "entry_id": entry_id,
        "message": "Lançamento confirmado e salvo com sucesso.",
    }


@app.get("/api/entries")
async def get_entries(
    start_date: str | None = None,
    end_date: str | None = None,
    entry_type: str | None = None,
    category: str | None = None,
    status: str | None = None,
):
    entries = list_entries(
        start_date=start_date,
        end_date=end_date,
        entry_type=entry_type,
        category=category,
        status=status,
    )

    receitas = sum(
        (entry.get("amount") or 0)
        for entry in entries
        if entry.get("entry_type") == "receita" and entry.get("status") != "cancelled"
    )
    despesas = sum(
        (entry.get("amount") or 0)
        for entry in entries
        if entry.get("entry_type") == "despesa" and entry.get("status") != "cancelled"
    )

    return {
        "ok": True,
        "entries": entries,
        "summary": {
            "receitas": round(receitas, 2),
            "despesas": round(despesas, 2),
            "saldo": round(receitas - despesas, 2),
            "total_registros": len(entries),
        },
    }


@app.put("/api/entries/{entry_id}")
async def update_entry_route(entry_id: int, payload: EntryPayload):
    update_entry(entry_id=entry_id, entry=payload.model_dump())
    return {"ok": True, "message": "Lançamento atualizado com sucesso."}


@app.delete("/api/entries/{entry_id}")
async def cancel_entry_route(entry_id: int):
    cancel_entry(entry_id=entry_id)
    return {"ok": True, "message": "Lançamento cancelado com sucesso."}
