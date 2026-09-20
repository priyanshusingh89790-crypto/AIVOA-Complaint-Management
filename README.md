# AIVOA Complaint Management System

AI-assisted pharmaceutical complaint management and quality workflow.

## What it does

AIVOA turns an unstructured customer complaint into a structured, reviewable QMS record.

**Workflow:** Intake → Document extraction → Validation → Classification → Risk triage → Investigation recommendations → QA review → Controlled record → Lifecycle tracking.

### Core capabilities

- Manual complaint intake
- PDF, DOCX, TXT and EML document analysis
- Groq-powered structured extraction and classification
- LangGraph multi-step AI workflow
- Preliminary risk assessment
- Investigation/CAPA recommendations
- Complaint history and detail views
- Duplicate/similarity detection against existing complaints
- Lifecycle: QA Review → Investigation → CAPA Review → Closed
- Audit trail for creation, AI analysis, status changes, CAPA recommendation and closure
- Operational analytics for volume, risk, category and status
- Human-in-the-loop quality workflow

## Architecture

```
React + Vite
    ↓ REST API
FastAPI
    ↓
LangGraph workflow
    ├── Extract
    ├── Validate
    ├── Classify
    ├── Risk
    └── Recommend
    ↓
Groq LLM
    ↓
PostgreSQL / SQLite fallback
```

## Repository

- `frontend/` — React/Vite QMS interface
- `backend/` — FastAPI API, LangGraph workflow and persistence

## Local setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev -- --port 5174
```

Open `http://localhost:5174`.

## Environment

Backend `.env`:

```env
GROQ_API_KEY=your_key
DATABASE_URL=postgresql://postgres:password@localhost:5432/aivoa_qms
LLM_MODEL=your_supported_groq_model
FRONTEND_URL=http://localhost:5174
```

Frontend `.env`:

```env
VITE_API_URL=http://localhost:8001/api
```

Never commit API keys.

## API

- `GET /api/health`
- `POST /api/analyze`
- `POST /api/analyze-document`
- `POST /api/duplicates`
- `POST /api/complaints`
- `GET /api/complaints`
- `GET /api/complaints/{id}`
- `PATCH /api/complaints/{id}/status`
- `GET /api/analytics`

## Important quality note

AI output is **preliminary decision support**. Final complaint disposition remains subject to human QA review. The system is a prototype and is not a validated pharmaceutical quality system.

## Demo flow

1. Load the sample complaint.
2. Analyze it.
3. Review extracted fields, completeness, classification and preliminary risk.
4. Check similar complaints.
5. Commit to QMS.
6. Open Complaint History.
7. Open the complaint detail.
8. Move it through Investigation/CAPA Review/Closed.
9. Open Analytics to review operational metrics.
