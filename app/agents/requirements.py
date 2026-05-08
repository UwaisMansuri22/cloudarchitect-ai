import json
import boto3
from botocore.config import Config
from app.config import REQUIREMENTS_MODEL, AWS_REGION
from app.models import ParsedRequirements

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
    config=Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 2})
)

SYSTEM_PROMPT = """You are an AWS solutions architect assistant. Extract structured requirements
from the user description. These requirements drive service selection, so be precise.

Return ONLY valid JSON matching this schema exactly:
{
  "use_case": "one sentence description",
  "scale": "small|medium|large|enterprise",
  "data_sensitivity": "public|internal|confidential|hipaa",
  "compute_preference": "serverless|container|ec2|mixed",
  "traffic_pattern": "steady|spiky|batch|streaming",
  "primary_patterns": ["pattern1"],
  "needs_search": false,
  "needs_realtime_streaming": false,
  "needs_relational_db": false,
  "is_public_facing": true,
  "needs_user_auth": false,
  "constraints": ["constraint1"],
  "suggested_regions": ["us-east-1"]
}

Inference rules:
- compute_preference: serverless if event-driven/API/low-traffic; container if stateful/long-running/microservices
- traffic_pattern: spiky if mentions Black Friday / burst / variable; streaming if IoT / analytics / real-time
- needs_search: true only if full-text product/content search is mentioned
- needs_realtime_streaming: true only if >1000 events/sec or real-time analytics is mentioned
- needs_relational_db: true if transactions, SQL, or relational data is mentioned
- is_public_facing: true if web app, API, customer-facing, SaaS, mobile backend; false if internal tool, batch job, data pipeline, intranet
- needs_user_auth: true if user accounts, login, signup, authentication, JWT, sessions, or multi-tenant is mentioned

No markdown. No explanation. Pure JSON only."""


def run_requirements_agent(state: dict) -> dict:
    """Parse requirements from user input"""
    try:
        description = state.get("description", "")
        constraints = state.get("constraints") or ""

        user_content = f"System description: {description}"
        if constraints:
            user_content += f"\n\nAdditional constraints: {constraints}"

        response = _bedrock.invoke_model(
            modelId=REQUIREMENTS_MODEL,
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_content}]
            })
        )

        body = json.loads(response["body"].read())
        raw = body["content"][0]["text"].strip()

        # Strip markdown fences if model ignores instructions
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)
        requirements = ParsedRequirements(**data)

        return {**state, "requirements": requirements, "current_agent": "architecture"}
    
    except Exception as e:
        print(f"Requirements agent error: {e}")
        # Return default requirements if parsing fails
        return {
            **state, 
            "requirements": ParsedRequirements(
                use_case="General AWS architecture",
                scale="medium",
                data_sensitivity="internal",
                primary_patterns=["microservices"],
                constraints=["budget constrained"],
                suggested_regions=["us-east-1"]
            ),
            "current_agent": "architecture",
            "error": f"Requirements parsing failed: {str(e)}"
        }