import os
import re
from datetime import datetime
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, Integer, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .services import analyze_complaint, read_upload

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aivoa_qms.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class ComplaintRecord(Base):
    __tablename__ = "complaints"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer: Mapped[str | None] = mapped_column(String(255))
    organization: Mapped[str | None] = mapped_column(String(255))
    product: Mapped[str | None] = mapped_column(String(255))
    batch: Mapped[str | None] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(120))
    summary: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), default="QA_REVIEW")
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(engine)

app = FastAPI(title="AIVOA Complaint Management API", version="1.2.0")
origins = [os.getenv("FRONTEND_URL", "http://localhost:5173"), "http://localhost:5174"]
app.add_middleware(CORSMiddleware, allow_origins=list(dict.fromkeys(origins)), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class ComplaintIn(BaseModel):
    customer: str = ""
    organization: str = ""
    product: str = ""
    batch: str = ""
    quantity: str = ""
    category: str = ""
    summary: str = ""
    description: str = Field(default="", max_length=20000)


class ComplaintCommitIn(ComplaintIn):
    analysis: dict[str, Any] | None = None


class StatusUpdateIn(BaseModel):
    status: str


class DuplicateCheckIn(BaseModel):
    product: str = ""
    batch: str = ""
    summary: str = ""
    description: str = ""


def audit(db, complaint_id: int, event_type: str, details: dict[str, Any] | None = None):
    db.add(AuditEvent(complaint_id=complaint_id, event_type=event_type, details=details or {}))


def tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", (value or "").lower()))


def similarity(a: dict[str, Any], b: ComplaintRecord) -> int:
    score = 0
    if a.get("batch") and b.batch and a["batch"].strip().lower() == b.batch.strip().lower():
        score += 45
    if a.get("product") and b.product and a["product"].strip().lower() == b.product.strip().lower():
        score += 25
    left = tokens(f'{a.get("summary","")} {a.get("description","")}')
    right = tokens(f'{b.summary or ""} {b.description or ""}')
    if left and right:
        score += round(30 * len(left & right) / max(1, len(left | right)))
    return min(100, score)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "AIVOA Complaint Management API", "version": app.version}


@app.post("/api/analyze")
def analyze(payload: ComplaintIn):
    return {"status": "ok", **analyze_complaint(payload.model_dump())}


@app.post("/api/analyze-document")
async def analyze_document(file: UploadFile = File(...)):
    allowed = {".pdf", ".txt", ".eml", ".docx"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Supported files: PDF, DOCX, TXT, EML")
    text = await read_upload(file)
    if not text:
        raise HTTPException(status_code=400, detail="The uploaded document contains no readable text")
    return {"status": "ok", "filename": file.filename, "source_text_preview": text[:500], **analyze_complaint({}, source_text=text)}


@app.post("/api/duplicates")
def duplicate_check(payload: DuplicateCheckIn):
    db = SessionLocal()
    try:
        rows = db.query(ComplaintRecord).order_by(ComplaintRecord.id.desc()).limit(100).all()
        matches = []
        for row in rows:
            score = similarity(payload.model_dump(), row)
            if score >= 35:
                matches.append({"id": row.id, "score": score, "customer": row.customer, "product": row.product, "batch": row.batch, "summary": row.summary, "status": row.status})
        return {"status": "ok", "matches": sorted(matches, key=lambda x: x["score"], reverse=True)[:5]}
    finally:
        db.close()


@app.post("/api/complaints")
def create_complaint(payload: ComplaintCommitIn):
    result = payload.analysis or analyze_complaint(payload.model_dump(exclude={"analysis"}))
    data = result.get("extracted") or payload.model_dump(exclude={"analysis"})
    db = SessionLocal()
    try:
        record = ComplaintRecord(
            customer=data.get("customer"), organization=data.get("organization"), product=data.get("product"),
            batch=data.get("batch"), category=data.get("category"), summary=data.get("summary"),
            description=data.get("description"), quantity=data.get("quantity"), analysis=result, status="QA_REVIEW",
        )
        db.add(record)
        db.flush()
        audit(db, record.id, "COMPLAINT_CREATED", {"status": "QA_REVIEW"})
        audit(db, record.id, "AI_ANALYSIS_COMPLETED", {"risk": result.get("risk", {}).get("level")})
        db.commit()
        db.refresh(record)
        return {"status": "ok", "id": record.id, "record_status": record.status, "analysis": result}
    finally:
        db.close()


@app.get("/api/complaints")
def list_complaints():
    db = SessionLocal()
    try:
        rows = db.query(ComplaintRecord).order_by(ComplaintRecord.id.desc()).limit(100).all()
        return {"status": "ok", "items": [{
            "id": r.id, "customer": r.customer, "product": r.product, "batch": r.batch,
            "category": r.category, "status": r.status,
            "risk": (r.analysis or {}).get("risk", {}).get("level"),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows]}
    finally:
        db.close()


@app.get("/api/complaints/{complaint_id}")
def get_complaint(complaint_id: int):
    db = SessionLocal()
    try:
        r = db.get(ComplaintRecord, complaint_id)
        if not r:
            raise HTTPException(status_code=404, detail="Complaint not found")
        events = db.query(AuditEvent).filter(AuditEvent.complaint_id == complaint_id).order_by(AuditEvent.id.asc()).all()
        return {"status": "ok", "item": {
            "id": r.id, "customer": r.customer, "organization": r.organization, "product": r.product,
            "batch": r.batch, "category": r.category, "summary": r.summary, "description": r.description,
            "quantity": r.quantity, "status": r.status, "analysis": r.analysis,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "audit": [{"id": e.id, "event_type": e.event_type, "details": e.details, "created_at": e.created_at.isoformat() if e.created_at else None} for e in events],
        }}
    finally:
        db.close()


@app.patch("/api/complaints/{complaint_id}/status")
def update_complaint_status(complaint_id: int, payload: StatusUpdateIn):
    allowed = {"QA_REVIEW", "INVESTIGATION", "CAPA_REVIEW", "CLOSED"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(sorted(allowed))}")
    db = SessionLocal()
    try:
        r = db.get(ComplaintRecord, complaint_id)
        if not r:
            raise HTTPException(status_code=404, detail="Complaint not found")
        old = r.status
        r.status = payload.status
        audit(db, complaint_id, "STATUS_CHANGED", {"from": old, "to": payload.status})
        if payload.status == "CAPA_REVIEW":
            audit(db, complaint_id, "CAPA_RECOMMENDED", {"actions": (r.analysis or {}).get("recommendation", {}).get("actions", [])})
        if payload.status == "CLOSED":
            audit(db, complaint_id, "COMPLAINT_CLOSED", {})
        db.commit()
        return {"status": "ok", "id": r.id, "record_status": r.status}
    finally:
        db.close()


@app.get("/api/analytics")
def analytics():
    db = SessionLocal()
    try:
        rows = db.query(ComplaintRecord).all()
        total = len(rows)
        statuses = {}
        risks = {}
        categories = {}
        for r in rows:
            statuses[r.status] = statuses.get(r.status, 0) + 1
            risk = (r.analysis or {}).get("risk", {}).get("level") or "UNKNOWN"
            risks[risk] = risks.get(risk, 0) + 1
            cat = r.category or (r.analysis or {}).get("classification", {}).get("category") or "Unclassified"
            categories[cat] = categories.get(cat, 0) + 1
        return {"status":"ok","total":total,"statuses":statuses,"risks":risks,"categories":dict(sorted(categories.items(), key=lambda x:x[1], reverse=True)[:8])}
    finally:
        db.close()
