import re
from datetime import date, datetime, timedelta

AMOUNT_PATTERN = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d{3})*,\d{2}|\d+[\.,]\d{2}|\d+)(?!\d)")
DATE_PATTERN = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")

CATEGORY_RULES = {
    "alimentacao": ["mercado", "supermercado", "padaria", "restaurante", "ifood", "lanche", "comida"],
    "moradia": ["aluguel", "condominio", "condomínio", "energia", "luz", "agua", "água", "internet", "gas", "gás"],
    "educacao": ["escola", "curso", "faculdade", "mensalidade escolar", "material escolar"],
    "saude": ["farmacia", "farmácia", "medico", "médico", "consulta", "plano de saude", "plano de saúde"],
    "transporte": ["uber", "99", "combustivel", "combustível", "gasolina", "estacionamento", "onibus", "ônibus"],
    "lazer": ["cinema", "streaming", "netflix", "spotify", "show", "viagem"],
    "receita": ["salario", "salário", "recebi", "entrada", "comissao", "comissão", "freelance", "pix recebido"],
}

PAYMENT_RULES = {
    "credito": ["crédito", "credito", "cartão de crédito", "cartao de credito"],
    "debito": ["débito", "debito", "cartão de débito", "cartao de debito"],
    "pix": ["pix"],
    "dinheiro": ["dinheiro", "espécie", "especie"],
    "boleto": ["boleto"],
}

EXPENSE_HINTS = [
    "paguei",
    "gastei",
    "comprei",
    "mercado",
    "aluguel",
    "escola",
    "farmacia",
    "farmácia",
    "uber",
    "conta",
]

INCOME_HINTS = [
    "recebi",
    "salario",
    "salário",
    "entrada",
    "comissao",
    "comissão",
    "reembolso",
]


def parse_amount(text: str) -> float | None:
    match = AMOUNT_PATTERN.search(text)
    if not match:
        return None

    raw = match.group(1).replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def parse_date(text: str, reference_date: date) -> str:
    normalized = text.lower()

    if "ontem" in normalized:
        return (reference_date - timedelta(days=1)).isoformat()

    if "hoje" in normalized:
        return reference_date.isoformat()

    match = DATE_PATTERN.search(normalized)
    if not match:
        return reference_date.isoformat()

    day = int(match.group(1))
    month = int(match.group(2))
    year_raw = match.group(3)

    if year_raw is None:
        year = reference_date.year
    elif len(year_raw) == 2:
        year = int(f"20{year_raw}")
    else:
        year = int(year_raw)

    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return reference_date.isoformat()


def detect_payment_method(text: str) -> str | None:
    normalized = text.lower()
    for method, keywords in PAYMENT_RULES.items():
        if any(keyword in normalized for keyword in keywords):
            return method
    return None


def detect_category(text: str) -> tuple[str | None, str | None]:
    normalized = text.lower()
    for category, keywords in CATEGORY_RULES.items():
        for keyword in keywords:
            if keyword in normalized:
                return category, keyword
    return None, None


def detect_entry_type(text: str, category: str | None) -> str | None:
    normalized = text.lower()

    if category == "receita":
        return "receita"

    if any(keyword in normalized for keyword in INCOME_HINTS):
        return "receita"

    if any(keyword in normalized for keyword in EXPENSE_HINTS):
        return "despesa"

    if category:
        return "despesa"

    return None


def score_confidence(amount: float | None, category: str | None, payment_method: str | None, entry_type: str | None) -> float:
    score = 0.15
    if amount is not None:
        score += 0.4
    if category:
        score += 0.2
    if payment_method:
        score += 0.1
    if entry_type:
        score += 0.15
    return round(min(score, 0.95), 2)


def split_candidate_lines(text: str) -> list[str]:
    candidates = [chunk.strip() for chunk in re.split(r"[\n;]+", text) if chunk.strip()]
    return candidates or ([text.strip()] if text.strip() else [])


def parse_text_entries(message_text: str, captured_at: str, submission_id: str) -> list[dict]:
    normalized_text = message_text.strip()
    if not normalized_text:
        return []

    reference_date = datetime.fromisoformat(captured_at).date()
    entries = []

    for chunk in split_candidate_lines(normalized_text):
        amount = parse_amount(chunk)
        category, subcategory = detect_category(chunk)
        entry_type = detect_entry_type(chunk, category)
        payment_method = detect_payment_method(chunk)
        occurred_on = parse_date(chunk, reference_date)
        confidence = score_confidence(amount, category, payment_method, entry_type)

        if amount is None and entry_type is None and category is None:
            continue

        entries.append(
            {
                "submission_id": submission_id,
                "captured_at": captured_at,
                "occurred_on": occurred_on,
                "source_kind": "text",
                "raw_text": chunk,
                "entry_type": entry_type or "indefinido",
                "amount": amount,
                "currency": "BRL",
                "category": category or "a_classificar",
                "subcategory": subcategory,
                "payment_method": payment_method,
                "description": chunk,
                "confidence": confidence,
            }
        )

    return entries
