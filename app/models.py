from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class ArchitectureRequest(BaseModel):
    description: str
    constraints: Optional[str] = None
    session_id: Optional[str] = None


class ParsedRequirements(BaseModel):
    use_case: str
    scale: Literal["small", "medium", "large", "enterprise"]
    data_sensitivity: Literal["public", "internal", "confidential", "hipaa"]
    primary_patterns: list[str]
    constraints: list[str]
    suggested_regions: list[str]


class AWSService(BaseModel):
    service_name: str
    aws_service_id: str
    purpose: str
    why_chosen: str
    tier: str


class Architecture(BaseModel):
    services: list[AWSService]
    pattern: str
    description: str


class CostLineItem(BaseModel):
    service: str
    monthly_cost_usd: float
    assumptions: str
    pricing_source: Literal["aws_pricing_api", "estimated"]


class SecurityItem(BaseModel):
    category: Literal["iam", "network", "encryption", "compliance", "monitoring"]
    recommendation: str
    priority: Literal["critical", "high", "medium", "low"]


class ArchitectureResult(BaseModel):
    session_id: str
    generated_at: datetime
    description: str
    requirements: ParsedRequirements
    architecture: Architecture
    mermaid_diagram: str
    cost_estimate: list[CostLineItem]
    total_monthly_cost_usd: float
    security_recommendations: list[SecurityItem]
    terraform_code: str
    generation_time_seconds: float
