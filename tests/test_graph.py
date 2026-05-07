import pytest
from unittest.mock import patch, MagicMock
from app.models import (
    ParsedRequirements, Architecture, AWSService,
    CostLineItem, SecurityItem
)


MOCK_REQUIREMENTS = ParsedRequirements(
    use_case="A scalable e-commerce platform",
    scale="large",
    data_sensitivity="internal",
    primary_patterns=["web api", "event driven"],
    constraints=["high availability"],
    suggested_regions=["us-east-1"]
)

MOCK_ARCHITECTURE = Architecture(
    services=[
        AWSService(
            service_name="API Gateway",
            aws_service_id="Amazon API Gateway",
            purpose="REST API endpoint",
            why_chosen="Managed, scalable HTTP API",
            tier="networking"
        ),
        AWSService(
            service_name="Lambda",
            aws_service_id="AWS Lambda",
            purpose="Business logic execution",
            why_chosen="Serverless, scales to zero",
            tier="compute"
        ),
        AWSService(
            service_name="DynamoDB",
            aws_service_id="Amazon DynamoDB",
            purpose="Product and order storage",
            why_chosen="Low latency, auto-scaling",
            tier="database"
        ),
    ],
    pattern="serverless",
    description="A serverless e-commerce backend using Lambda and DynamoDB."
)

MOCK_COST_ITEMS = [
    CostLineItem(
        service="Amazon API Gateway",
        monthly_cost_usd=3.50,
        assumptions="1M requests/month",
        pricing_source="aws_pricing_api"
    ),
    CostLineItem(
        service="AWS Lambda",
        monthly_cost_usd=0.00,
        assumptions="Under free tier",
        pricing_source="aws_pricing_api"
    ),
    CostLineItem(
        service="Amazon DynamoDB",
        monthly_cost_usd=1.25,
        assumptions="On-demand pricing",
        pricing_source="aws_pricing_api"
    ),
]

MOCK_SECURITY = [
    SecurityItem(
        category="iam",
        recommendation="Apply least-privilege IAM policies to Lambda execution roles.",
        priority="critical"
    ),
    SecurityItem(
        category="encryption",
        recommendation="Enable DynamoDB encryption at rest using AWS KMS.",
        priority="high"
    ),
]

MOCK_TERRAFORM = """terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
"""

MOCK_MERMAID = """flowchart LR
  subgraph Networking
    APIGateway[API Gateway]
  end
  subgraph Compute
    Lambda[Lambda]
  end
  APIGateway --> Lambda
"""


def make_bedrock_response(text: str):
    import json as _json
    mock_response = MagicMock()
    mock_response["body"].read.return_value = _json.dumps(
        {"content": [{"text": text}]}
    ).encode()
    return mock_response


@pytest.fixture
def mock_bedrock():
    with patch("boto3.client") as mock_client:
        client = MagicMock()
        mock_client.return_value = client
        yield client


def test_requirements_agent(mock_bedrock):
    import json
    payload = {
        "use_case": "A scalable e-commerce platform",
        "scale": "large",
        "data_sensitivity": "internal",
        "primary_patterns": ["web api"],
        "constraints": [],
        "suggested_regions": ["us-east-1"]
    }
    mock_bedrock.invoke_model.return_value = make_bedrock_response(json.dumps(payload))

    from app.agents.requirements import run_requirements_agent
    state = {
        "description": "E-commerce platform",
        "constraints": None,
        "session_id": "test-123",
        "start_time": 0.0,
        "requirements": None,
        "architecture": None,
        "mermaid_diagram": None,
        "cost_estimate": None,
        "security_recommendations": None,
        "terraform_code": None,
        "current_agent": "requirements",
        "error": None
    }
    result = run_requirements_agent(state)
    assert result["requirements"].scale == "large"
    assert result["current_agent"] == "architecture"


def test_pricing_lookup():
    from app.pricing import get_pricing_for_services
    items = get_pricing_for_services(["AWS Lambda", "Amazon S3", "Amazon DynamoDB"])
    assert len(items) == 3
    assert items[0].service == "AWS Lambda"
    assert items[0].monthly_cost_usd == 0.00
    assert items[0].pricing_source == "aws_pricing_api"


def test_pricing_unknown_service():
    from app.pricing import get_pricing_for_services
    items = get_pricing_for_services(["Some Unknown Service"])
    assert len(items) == 1
    assert items[0].pricing_source == "estimated"
    assert items[0].monthly_cost_usd == 10.00


def test_graph_state_structure():
    from app.graph import GraphState
    state: GraphState = {
        "description": "test",
        "constraints": None,
        "session_id": "abc",
        "start_time": 0.0,
        "requirements": None,
        "architecture": None,
        "mermaid_diagram": None,
        "cost_estimate": None,
        "security_recommendations": None,
        "terraform_code": None,
        "current_agent": "requirements",
        "error": None
    }
    assert state["session_id"] == "abc"
    assert state["current_agent"] == "requirements"


def test_cost_total_calculation():
    total = sum(item.monthly_cost_usd for item in MOCK_COST_ITEMS)
    assert abs(total - 4.75) < 0.01


def test_architecture_tier_grouping():
    tiers = {}
    for s in MOCK_ARCHITECTURE.services:
        tiers.setdefault(s.tier, []).append(s)
    assert "compute" in tiers
    assert "database" in tiers
    assert "networking" in tiers
