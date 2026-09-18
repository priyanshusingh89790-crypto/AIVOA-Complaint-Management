from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

ProductType = Literal["API", "FDF", "Unknown"]
RiskLevel = Literal["Low", "Medium", "High", "Critical", "Unknown"]

class Complainant(BaseModel):
    name: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class ProductInfo(BaseModel):
    name: Optional[str] = None
    product_type: ProductType = "Unknown"
    strength_grade: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    affected_quantity: Optional[str] = None

class DefectInfo(BaseModel):
    category: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    originating_site: Optional[str] = None
    impacted_material: Optional[str] = None

class RiskAssessment(BaseModel):
    severity: RiskLevel = "Unknown"
    risk_level: RiskLevel = "Unknown"
    risk_summary: Optional[str] = None
    risk_factors: list[str] = Field(default_factory=list)
    suggested_next_action: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)

class ComplaintAnalysis(BaseModel):
    source: Optional[str] = None
    complainant: Complainant = Field(default_factory=Complainant)
    product: ProductInfo = Field(default_factory=ProductInfo)
    defect: DefectInfo = Field(default_factory=DefectInfo)
    missing_fields: list[str] = Field(default_factory=list)
    completeness_score: float = Field(default=0, ge=0, le=1)
    summary: Optional[str] = None
    risk: RiskAssessment = Field(default_factory=RiskAssessment)
    recommendations: list[str] = Field(default_factory=list)

class AnalyzeTextRequest(BaseModel):
    text: str = Field(min_length=10, max_length=30000)
    source: str = "Copilot"

class ComplaintCreate(BaseModel):
    source: Optional[str] = None
    complainant: Complainant = Field(default_factory=Complainant)
    product: ProductInfo = Field(default_factory=ProductInfo)
    defect: DefectInfo = Field(default_factory=DefectInfo)
    summary: Optional[str] = None
    risk: RiskAssessment = Field(default_factory=RiskAssessment)
    ai_analysis: Optional[ComplaintAnalysis] = None

class ComplaintResponse(ComplaintCreate):
    id: int
    complaint_number: str
    status: str
    created_at: datetime
    updated_at: datetime