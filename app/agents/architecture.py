import json
import boto3
from botocore.config import Config
from app.config import ARCHITECTURE_MODEL, AWS_REGION
from app.models import Architecture, AWSService

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
    config=Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 2})
)

SYSTEM_PROMPT = """You are a senior AWS solutions architect with 10+ years experience designing
production systems. Select the optimal AWS services for the given requirements.

For each service include:
- Why you chose it over alternatives
- How it connects to other services
- Any configuration recommendations

Return ONLY valid JSON:
{
  "services": [
    {
      "service_name": "display name",
      "aws_service_id": "exact AWS service name",
      "purpose": "what it does in this architecture",
      "why_chosen": "why this over alternatives",
      "tier": "compute|storage|networking|database|messaging|monitoring"
    }
  ],
  "pattern": "serverless|microservices|event-driven|monolithic|hybrid",
  "description": "2-3 sentence architecture summary"
}
No markdown. Pure JSON only."""


def run_architecture_agent(state: dict) -> dict:
    requirements = state["requirements"]

    user_content = f"""Design an AWS architecture for these requirements:

Use case: {requirements.use_case}
Scale: {requirements.scale}
Data sensitivity: {requirements.data_sensitivity}
Patterns needed: {', '.join(requirements.primary_patterns)}
Constraints: {', '.join(requirements.constraints) if requirements.constraints else 'none'}
Preferred regions: {', '.join(requirements.suggested_regions)}"""

    response = _bedrock.invoke_model(
        modelId=ARCHITECTURE_MODEL,
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
    services = [AWSService(**s) for s in data["services"]]
    architecture = Architecture(
        services=services,
        pattern=data["pattern"],
        description=data["description"]
    )

    return {**state, "architecture": architecture, "current_agent": "diagram"}
