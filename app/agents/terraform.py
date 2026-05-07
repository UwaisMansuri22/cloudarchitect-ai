import json
import boto3
from botocore.config import Config
from app.config import TERRAFORM_MODEL, AWS_REGION

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
    config=Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 2})
)

SYSTEM_PROMPT = """You are a Terraform expert. Generate production-ready Terraform HCL for the
AWS architecture provided.

Requirements:
- Use AWS provider ~> 5.0
- Use variables for all configurable values
- Include outputs for all important resource identifiers
- Add tags to all resources: Environment, Project, ManagedBy=Terraform
- Include comments explaining non-obvious configuration choices
- Use data sources where appropriate (e.g. current region, account ID)
- Apply security best practices from the security recommendations

Return ONLY the raw Terraform HCL code.
No markdown fences. No explanation. Start with terraform { block."""


def run_terraform_agent(state: dict) -> dict:
    architecture = state["architecture"]
    requirements = state["requirements"]
    security_recs = state.get("security_recommendations") or []

    services_text = "\n".join(
        f"- {s.aws_service_id}: {s.purpose} | {s.why_chosen}"
        for s in architecture.services
    )

    critical_security = "\n".join(
        f"- [{r.priority.upper()}] {r.category}: {r.recommendation}"
        for r in security_recs
        if r.priority in ("critical", "high")
    )

    user_content = f"""Generate Terraform HCL for this AWS architecture:

Pattern: {architecture.pattern}
Description: {architecture.description}
Scale: {requirements.scale}
Data sensitivity: {requirements.data_sensitivity}
Region: {requirements.suggested_regions[0] if requirements.suggested_regions else 'us-east-1'}

Services to provision:
{services_text}

Critical security requirements:
{critical_security if critical_security else 'Standard security best practices'}"""

    response = _bedrock.invoke_model(
        modelId=TERRAFORM_MODEL,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_content}]
        })
    )

    body = json.loads(response["body"].read())
    raw = body["content"][0]["text"].strip()

    # Strip markdown fences
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("hcl") or raw.startswith("terraform"):
            raw = raw.split("\n", 1)[1]
    raw = raw.strip()

    return {**state, "terraform_code": raw, "current_agent": "done"}
