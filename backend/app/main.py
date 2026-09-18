import os
from datetime import datetime
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, Integer, String, Text, create_engine
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


Base.metadata.create_all(engine)

app = FastAPI(title="AIVOA Complaint Management API", version="1.1.0")

origins = [os.getenv("FRONTEND_URL", "http://localhost:5173"), "http://localhost:5174"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ComplaintIn(BaseModel):
    customer: str = ""
    organization: str = ""
    product: str = ""
    batch: str = ""
    quantity: str = ""
    category: str = ""
    summary: str = ""
    description: str = Field(default="", max_length=20000)


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
    return {
        "status": "ok",
        "filename": file.filename,
        "source_text_preview": text[:500],
        **analyze_complaint({}, source_text=text),
    }


@app.post("/api/complaints")
def create_complaint(payload: ComplaintIn):
    result = analyze_complaint(payload.model_dump())
    data = result["extracted"]
    db = SessionLocal()
    try:
        record = ComplaintRecord(
            customer=data.get("customer"),
            organization=data.get("organization"),
            product=data.get("product"),
            batch=data.get("batch"),
            category=data.get("category"),
            summary=data.get("summary"),
            description=data.get("description"),
            quantity=data.get("quantity"),
            analysis=result,
            status="QA_REVIEW",
        )
        db.add(record)
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
        return {
            "status": "ok",
            "items": [
                {
                    "id": r.id,
                    "customer": r.customer,
                    "product": r.product,
                    "batch": r.batch,
                    "category": r.category,
                    "status": r.status,
                    "risk": (r.analysis or {}).get("risk", {}).get("level"),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ],
        }
    finally:
        db.close()
