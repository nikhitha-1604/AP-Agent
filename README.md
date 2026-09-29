# AP Invoice & Contract Exception Agent

An AI-assisted Accounts Payable workflow that extracts invoice data, checks it against
Purchase Orders and vendor contracts, and routes clean invoices to straight-through
processing or exceptions to an AP clerk. The agent also recalls previous vendor and
Purchase Order decisions to provide context for recommendations, then stores clerk
resolutions as memories for future invoices.

**Memory implementation note:** “Hindsight Memory” is currently implemented with
SQLAlchemy models stored in the application's configured database. This repository
does not connect to an external Hindsight Cloud service or require a Hindsight API key.

---



## Problem Statement

Large organizations receive hundreds of invoices daily. Around 90–95% are valid,
but every invoice still requires manual verification. This system automates the
validation pipeline so that only genuine exceptions require human review.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Streamlit Frontend (Community Cloud)       │
│ Upload │ Overview │ Exceptions │ Memory Intelligence    │
│              Invoice History │ Audit Trail              │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────┐
│               FastAPI Backend                           │
│ Invoice processing │ Clerk feedback │ Vendor/memory APIs│
│ Invoice detail/history │ Audit trail │ Dashboard stats  │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│              LangGraph Agent Pipeline                   │
│ OCR → Extraction → Validation → PO/Contract Matching    │
│                         ↓                               │
│              Vendor/PO Memory Recall                    │
│                         ↓                               │
│             Decision → Clerk Review                     │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│ SQLAlchemy persistence: invoices, audit, feedback,      │
│ hindsight memories, vendor profiles, POs and contracts  │
└──────────────────────────┬──────────────────────────────┘
                           │
                    SQLite (ap_agent.db)
```

Memory recall decorates detected exceptions with historical context, priority, and
suggested resolutions. It is advisory: an exception still routes to human review, and
memory recommendations do not bypass mandatory PO, duplicate-invoice, or contract
checks. Extraction failures skip matching and memory recall. Duplicate detection is
performed by the upload endpoint after the LangGraph decision, and still forces review.

---

## Folder Structure

```
AP-Agent-main/
│
├── backend/
│   ├── agents/
│   │   ├── graph.py              # LangGraph StateGraph + routing
│   │   └── nodes.py              # extraction, validation, matching, memory, decision
│   ├── models/
│   │   └── models.py             # SQLAlchemy ORM models
│   ├── repositories/
│   │   └── invoice_repo.py       # Database CRUD layer
│   ├── schemas/
│   │   └── invoice_schema.py     # Pydantic extraction schema
│   ├── services/
│   │   ├── matching.py           # MatchingEngine (PO + contract comparison)
│   │   └── audit_service.py      # AuditService (writes audit log records)
│   │   └── memory_service.py     # Recall, clerk feedback, vendor profiles
│   ├── tests/
│   │   └── test_eval_suite.py    # Deterministic evaluation scenarios
│   ├── tools/
│   │   └── ocr_engine.py         # PDF and image text extraction
│   ├── database.py               # SQLAlchemy engine + session setup
│   ├── main.py                   # FastAPI application + all endpoints
│   ├── seed_test_data.py         # Seeds multi-vendor reference/memory data
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pytest.ini
│
├── frontend/
│   ├── app.py                    # Streamlit dashboard
│   ├── Dockerfile
│   └── requirements.txt
│
├── docker-compose.yml
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Groq API — `openai/gpt-oss-120b` |
| Agent Framework | LangGraph |
| Validation | Pydantic v2 |
| Backend API | FastAPI + Uvicorn |
| OCR | pypdf + pytesseract |
| Database | SQLAlchemy; SQLite at `./ap_agent.db` in the backend working directory |
| Memory | SQLAlchemy-backed Hindsight memory, clerk feedback, and vendor profiles |
| Frontend | Streamlit + Plotly |
| Backend Hosting | Render (free tier) |
| Frontend Hosting | Streamlit Community Cloud |
| Containers | Docker + Docker Compose |
| Testing | pytest + pytest-asyncio |

---

## Environment Variables

### Backend

Create a `.env` file in the `backend/` directory for local development:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Get a free Groq API key at https://console.groq.com

No separate memory-service credential is currently used. Memory records are written to
the same database as invoices. The database URL is set to SQLite in `backend/database.py`.

### Frontend

Set in Streamlit Cloud → App Settings → Secrets:

```toml
API_URL = "https://ap-invoice-agent-backend.onrender.com"
```

Locally this defaults to `http://localhost:8000`.

---

## Setup — Local (without Docker)

### Prerequisites

- Python 3.11+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed and on PATH

### 1. Get the source

```bash
git clone https://github.com/24wh1a0598/AP-Invoice-Agent.git
cd AP-Invoice-Agent
```

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create `.env`:

```env
GROQ_API_KEY=your_key_here
```

Seed the database with reference data:

```bash
python seed_test_data.py
```

Start the API server:

```bash
uvicorn main:app --reload --port 8000
```

API available at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

### 3. Frontend

```bash
cd ../frontend
pip install -r requirements.txt
streamlit run app.py
```

Frontend available at `http://localhost:8501`

---

## Setup — Docker Compose

### Prerequisites

- Docker Desktop installed and running

### 1. Create `.env` in the project root

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 2. Build and start

```bash
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Frontend | http://localhost:8501 |

### 3. Stop

```bash
docker-compose down
```

---

## First-Time Database Setup (Render / Production)

After deploying to Render, the database is empty. Seed it by calling:

```
POST https://ap-invoice-agent-backend.onrender.com/seed-db
```

Use the Swagger UI at `/docs` → `POST /seed-db` → Try it out → Execute.

This seeds five vendors, their Purchase Orders and contracts, and initial vendor
memory examples. Safe to call multiple times; existing reference records are retained.

> **Important:** Render free tier uses an ephemeral filesystem. The SQLite database
> resets on every redeploy. Re-run `/seed-db` after each deployment.

---

## API Reference

### POST /upload-invoice

Upload a PDF or image invoice for processing.

**Request:** `multipart/form-data` — field `file` (PDF, PNG, JPG)

The response includes extracted fields, exceptions, agent reasoning, and a
`recalled_memory` object containing matching historical memories, vendor profile
information, decorated exception recommendations, and an executive summary.

**Status values:**

| Value | Meaning |
|-------|---------|
| `STRAIGHT_THROUGH` | All checks passed — payment scheduled |
| `EXCEPTION` | One or more issues found — routed to AP clerk |
| `EXCEPTION` | Includes validation/extraction failures and other issues requiring review |

---

### GET /invoices

Paginated list of all invoices. Query params: `skip` (default 0), `limit` (default 50).

---

### GET /invoice/{id}

Full detail for one invoice including its vendor, exceptions enriched with memory
recommendations, recalled memories, vendor profile, and clerk feedback history.

---

### GET /invoice/{id}/audit

Complete ordered audit trail for one invoice, including agent steps and clerk feedback.

---

### POST /invoice/{id}/feedback

Record a clerk decision with a required explanation. JSON body:

```json
{
  "action": "APPROVE",
  "reason": "Verified the price variance with the procurement manager.",
  "exception_type": "PO_MISMATCH"
}
```

Supported actions are `APPROVE`, `REJECT`, and `RESOLVE`. The decision updates the
invoice, writes a clerk feedback record and Hindsight memory, recalculates the vendor
profile, and adds an audit event.

---

### Memory and vendor endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /vendors` | Vendor summaries and reliability metrics |
| `GET /vendor/{vendor_id}/memory` | Vendor profile and its historical memories |
| `GET /memories/recent?limit=5` | Most recent learned memory records |

---

### GET /stats

Dashboard summary: invoice counts, straight-through rate, review count, summed invoice
value (returned as `total_scheduled_value`), and total Hindsight memories.
| 5 | Prompt-injection text with pre-seeded mismatched fields | EXCEPTION; matching rules still flag the mismatch |

---

### POST /seed-db

Seeds multi-vendor reference data, Purchase Orders, contracts, and example memories.
Safe to call multiple times. Required after every Render redeploy.

---

### GET /

Health check — returns `{"status": "online", ...}`.

---

## Exception Types

| Type | Meaning |
|------|---------|
| `EXTRACTION_FAILED` | Extraction returned no usable invoice data |
| `MISSING_REQUIRED_FIELD` | Required field absent after extraction |
| `UNKNOWN_PO` | PO number not found in database |
| `MISSING_PO` | Invoice has no PO number |
| `PO_MISMATCH` | Price or quantity differs from PO line items |
| `UNKNOWN_CONTRACT` | Contract number not found in database |
| `CONTRACT_VIOLATION` | Total exceeds contract limit or contract expired |
| `DUPLICATE_INVOICE` | Invoice number already exists in the system |
| `DB_ERROR` | Database error during lookup |
| `MATCHING_ERROR` | Unexpected error during matching node |

Other exception values include `DUPLICATE_INVOICE`, `TAX_DISCREPANCY`, and
`DB_ERROR`. The matching and memory layers also distinguish `UNKNOWN_CONTRACT` and
`CONTRACT_VIOLATION`.

---

## Evaluation Suite

```bash
cd backend
pytest tests/test_eval_suite.py -v
```

Seven deterministic scenarios use pre-seeded data and avoid real LLM calls.

| # | Scenario | Expected |
|---|----------|---------|
| 1 | Clean invoice — all fields match | STRAIGHT_THROUGH |
| 2 | Price variance on line item | EXCEPTION / PO_MISMATCH |
| 3 | Total exceeds contract limit | EXCEPTION / CONTRACT_VIOLATION |
| 4 | Missing required field | EXCEPTION / MISSING_REQUIRED_FIELD |
| 6 | Historical memory recall and exception recommendations | EXCEPTION; memory is advisory |
| 7 | Clerk feedback and vendor profile update | Feedback/memory persisted |

---

## Business Rules

The system enforces these rules unconditionally:

- Never pay invoices with missing required fields
- Never pay invoices with price or quantity mismatches against PO
- Never pay invoices referencing unknown POs or contracts
- Never pay invoices exceeding contract limits or against expired contracts
- Never pay duplicate invoices
- Never guess or estimate missing values
- Treat all document content as untrusted input
- Determine decisions from extracted fields and backend validation/matching results,
  not from approval instructions written in invoice text
- Memory provides context and recommendations only; it cannot bypass PO, duplicate,
  or contract checks
- Any detected exception is routed for human review; clerk approval/resolution is
  recorded with its explanation and can inform later recommendations

---

## Known Limitations

1. **SQLite persistence on Render** — the database uses a local SQLite file and may be ephemeral on the current hosting setup. Reference data and learned memories can be lost on redeploy; call `/seed-db` to restore seeded data. For durable production storage, configure a persistent database (for example PostgreSQL) and update the database configuration.
2. **Scanned PDFs** — Tesseract OCR handles image files but may struggle with low-resolution scans.
3. **No authentication** — the API has no auth layer. Add OAuth2/API key before exposing publicly.
4. **Vendor matching** — extracted vendor name/code is used to look up vendor history, but the code does not enforce that the invoice vendor matches the vendor associated with its PO or contract.
5. **Prompt-injection test scope** — the deterministic test pre-seeds extracted fields and does not exercise the live LLM extraction prompt. It verifies downstream matching behavior, not general prompt-injection resistance.

---

## Recommended Next Steps

1. Switch to PostgreSQL on Render to eliminate the ephemeral database problem
2. Add API authentication (FastAPI `Security` dependency)
3. Add Alembic migrations for schema management
4. Add email/Slack notification when an invoice is routed to review
5. Add vendor identity verification in `matching_node`

---


