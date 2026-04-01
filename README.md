# Consultor Financeiro Local

Projeto local e open source para lançamento, revisão, confirmação e consulta de orçamento familiar.

## O que já está pronto

- captura por texto, áudio, imagem e PDF
- interpretação inicial do texto
- revisão manual antes de salvar
- histórico com filtros
- edição e cancelamento de lançamentos
- banco local em SQLite

## O que mudou nesta versão

A camada de interpretação foi preparada para usar **IA local**.

Fluxo atual de interpretação:

1. tenta interpretar com um modelo local via **Ollama**
2. se a IA local não estiver disponível, cai automaticamente no parser por regras

Assim o sistema continua funcionando mesmo sem a IA instalada.

## Stack

- **FastAPI**
- **Pydantic**
- **SQLite**
- **HTML + CSS + JavaScript**
- **httpx** para comunicação com modelo local

## Como rodar

### 1. Criar ambiente virtual

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar dependências

```powershell
python -m pip install -r requirements.txt
```

### 3. Executar a aplicação

```powershell
python -m uvicorn app.main:app --reload
```

### 4. Abrir no navegador

```text
http://127.0.0.1:8000
```

## Ativando interpretação com IA local

Crie um arquivo `.env` com base no `.env.example`.

Exemplo:

```env
INTERPRETER_MODE=auto
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=60
```

### Modos disponíveis

- `rules` → usa só o parser por regras
- `auto` → tenta IA local e cai no parser por regras se falhar
- `ai` → tenta IA local primeiro; neste projeto ainda mantém fallback para não quebrar o fluxo

## Estrutura

```text
app/
  main.py
  services/
    database.py
    parser.py
    llm_parser.py
    interpreter.py
    storage.py
static/
  styles.css
  app.js
templates/
  index.html
data/
  db/
  inbox/
  submissions/
```

## Observação

A interface continua igual. A virada está na camada de interpretação.
