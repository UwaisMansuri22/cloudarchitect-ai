import json
import boto3
from botocore.config import Config
from app.config import SECURITY_MODEL, AWS_REGION
from app.models import SecurityItem

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
    config=Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 2})
)

SYSTEM_PROMPT = """You are an AWS security architect. Review the architecture and generate specific,
actionable security recommendations.

Cover: IAM least-privilege, VPC design, encryption at rest and in transit,
compliance considerations, monitoring and alerting.

For healthcare/HIPAA systems include: PHI handling, audit logging, BAA requirements.

Return ONLY valid JSON:
{
  "recommendations": [
    {
      "category": "iam|network|encryption|compliance|monitoring",
      "recommendation": "specific actionable recommendation",
      "priority": "critical|high|medium|low"
    }
  ]
}
No markdown. Pure JSON only."""


def run_security_agent(state: dict) -> dict:
    architecture = state["architecture"]
    requirements = state["requirements"]

    services_text = "\n".join(
        f"- {s.aws_service_id}: {s.purpose}"
        for s in architecture.services
    )

    user_content = f"""Architecture pattern: {architecture.pattern}
Data sensitivity: {requirements.data_sensitivity}
Scale: {requirements.scale}
Constraints: {', '.join(requirements.constraints) if requirements.constraints else 'none'}

Services in use:
{services_text}

Architecture description: {architecture.description}

Generate security recommendations for this architecture."""

    response = _bedrock.invoke_model(
        modelId=SECURITY_MODEL,
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

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)
    recommendations = [SecurityItem(**r) for r in data["recommendations"]]

    return {**state, "security_recommendations": recommendations, "current_agent": "terraform"}
