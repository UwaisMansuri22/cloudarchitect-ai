import json
import boto3
from botocore.config import Config
from app.config import COST_MODEL, AWS_REGION
from app.models import CostLineItem
from app.pricing import get_pricing_for_services

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
    config=Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 2})
)

SYSTEM_PROMPT = """You are an AWS cost analyst. You have been given pricing data for AWS services.
Review the cost items and return them as valid JSON with any corrections or additional context.

Return ONLY valid JSON:
{
  "items": [
    {
      "service": "service name",
      "monthly_cost_usd": 0.00,
      "assumptions": "detailed assumptions about usage",
      "pricing_source": "aws_pricing_api|estimated"
    }
  ]
}
No markdown. Pure JSON only."""


def run_cost_agent(state: dict) -> dict:
    """Estimate costs for the architecture"""
    try:
        architecture = state.get("architecture")
        requirements = state.get("requirements")

        if not architecture or not requirements:
            return {**state, "cost_estimate": [], "current_agent": "security"}

        service_names = [s.aws_service_id for s in architecture.services]
        pricing_items = get_pricing_for_services(service_names)

        pricing_text = "\n".join(
            f"- {item.service}: ${item.monthly_cost_usd:.2f}/month ({item.assumptions})"
            for item in pricing_items
        )

        user_content = f"""Architecture pattern: {architecture.pattern}
Scale: {requirements.scale}

AWS Pricing data retrieved:
{pricing_text}

Review these costs for the described architecture and return the JSON cost breakdown."""

        response = _bedrock.invoke_model(
            modelId=COST_MODEL,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
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

        try:
            data = json.loads(raw)
            cost_items = [CostLineItem(**item) for item in data.get("items", [])]
        except Exception:
            cost_items = pricing_items

        return {**state, "cost_estimate": cost_items, "current_agent": "security"}
    
    except Exception as e:
        return {**state, "error": f"Cost agent failed: {str(e)}", "current_agent": "security"}