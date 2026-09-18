import json
import os
from typing import Any, TypedDict

from dotenv import load_dotenv
from fastapi import UploadFile
from groq import Groq
from langgraph.graph import END, StateGraph
from pypdf import PdfReader

load_dotenv()
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")

class ComplaintState(TypedDict, total=False):
    complaint: dict[str, Any]
    source_text: str
    extracted: dict[str, Any]
    validation: dict[str, Any]
    classification: dict[str, Any]
    risk: dict[str, Any]
    recommendation: dict[str, Any]

def _client():
    key = os.getenv("GROQ_API_KEY")
    return Groq(api_key=key) if key else None

def _json_call(system: str, payload: Any) -> dict[str, Any]:
    client = _client()
    if not client:
        return {}
    response = client.chat.completions.create(
        model=MODEL, temperature=0, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    return json.loads(response.choices[0].message.content)

def extract_text(data: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        import io
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if name.endswith(".docx"):
        from docx import Document
        import io
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    return data.decode("utf-8", errors="replace").strip()

async def read_upload(file: UploadFile) -> str:
    return extract_text(await file.read(), file.filename or "document.txt")

def extract_node(state: ComplaintState):
    complaint, source = state.get("complaint", {}), state.get("source_text", "")
    if not source:
        return {"extracted": complaint}
    result = _json_call("Extract pharmaceutical complaint fields: customer, organization, product, batch, quantity, category, summary, description. Return JSON only. Use null for missing values; never invent facts.", {"document": source[:20000]})
    return {"extracted": result or complaint}

def validate_node(state: ComplaintState):
    data = state.get("extracted", {})
    required = ["customer", "product", "batch", "summary", "description"]
    missing = [k for k in required if not data.get(k)]
    return {"validation": {"complete": not missing, "missing_fields": missing, "completeness": round((len(required)-len(missing))/len(required)*100)}}

def classify_node(state: ComplaintState):
    data = state.get("extracted", {})
    result = _json_call("Classify a pharmaceutical complaint. Return JSON with category, defect_type, rationale. Use concise factual language.", data)
    return {"classification": result or {"category": data.get("category") or "Product Quality", "defect_type": "Unclassified", "rationale": "LLM unavailable; QA review required."}}

def risk_node(state: ComplaintState):
    data = state.get("extracted", {})
    result = _json_call("Assess preliminary complaint risk for QA triage. Return JSON with level (LOW, MEDIUM, HIGH, CRITICAL), factors array, rationale. This is provisional, not a final quality decision. Use only supplied facts.", data)
    return {"risk": result or {"level": "MEDIUM", "factors": ["AI assessment unavailable"], "rationale": "Provisional triage level; QA review required."}}

def recommendation_node(state: ComplaintState):
    payload = {"complaint": state.get("extracted", {}), "classification": state.get("classification", {}), "risk": state.get("risk", {})}
    result = _json_call("Suggest next QA investigation actions for a pharmaceutical complaint. Return JSON with actions array and rationale. Do not make a final disposition.", payload)
    return {"recommendation": result or {"actions": ["Review batch records", "Check complaint history", "Escalate to QA if evidence indicates systemic impact"], "rationale": "Provisional recommendations; QA approval required."}}

graph = StateGraph(ComplaintState)
graph.add_node("extract", extract_node); graph.add_node("validate", validate_node); graph.add_node("classify", classify_node); graph.add_node("risk", risk_node); graph.add_node("recommend", recommendation_node)
graph.set_entry_point("extract"); graph.add_edge("extract", "validate"); graph.add_edge("validate", "classify"); graph.add_edge("classify", "risk"); graph.add_edge("risk", "recommend"); graph.add_edge("recommend", END)
WORKFLOW = graph.compile()

def analyze_complaint(complaint: dict[str, Any], source_text: str = "") -> dict[str, Any]:
    result = WORKFLOW.invoke({"complaint": complaint, "source_text": source_text})
    return {k: result.get(k, {}) for k in ("extracted", "validation", "classification", "risk", "recommendation")}
