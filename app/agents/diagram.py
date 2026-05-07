import json
import boto3
from botocore.config import Config
from app.config import DIAGRAM_MODEL, AWS_REGION

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
    config=Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 2})
)

SYSTEM_PROMPT = """Convert the AWS architecture into a valid Mermaid flowchart diagram.
Use LR (left-right) direction.
Group services by tier using subgraphs.
Show data flow with labeled arrows.
Return ONLY the raw Mermaid code starting with 'flowchart LR'.
No markdown fences. No explanation.

Example format:
flowchart LR
  subgraph Networking
    APIGateway[API Gateway]
    CloudFront[CloudFront]
  end
  subgraph Compute
    Lambda[Lambda Function]
  end
  CloudFront --> APIGateway
  APIGateway --> Lambda"""


def run_diagram_agent(state: dict) -> dict:
    architecture = state["architecture"]

    services_text = "\n".join(
        f"- {s.service_name} ({s.tier}): {s.purpose}"
        for s in architecture.services
    )

    user_content = f"""Architecture pattern: {architecture.pattern}
Description: {architecture.description}

Services:
{services_text}

Generate a Mermaid flowchart showing the data flow between these services."""

    response = _bedrock.invoke_model(
        modelId=DIAGRAM_MODEL,
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

    # Strip markdown fences
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("mermaid"):
            raw = raw[7:]
    raw = raw.strip()

    # Ensure it starts with flowchart
    if not raw.startswith("flowchart"):
        raw = "flowchart LR\n" + raw

    return {**state, "mermaid_diagram": raw, "current_agent": "cost"}
