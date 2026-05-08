# CloudArchitect AI

A multi-agent AI system that turns a plain-English description of your system into a complete AWS architecture — including service selection, Mermaid diagram, real cost estimates, security recommendations, and production-ready Terraform code.

Built with **LangGraph**, **Amazon Bedrock**, and **FastAPI**. Deployable as an AWS Lambda function behind API Gateway, or run locally with Uvicorn.

---

## How it works

You describe what you're building. Six specialized AI agents run sequentially, each handing enriched state to the next:

```
Requirements → Architecture → Diagram → Cost → Security → Terraform
```

| # | Agent | What it does |
|---|-------|-------------|
| 1 | **Requirements** | Parses your description into structured requirements: scale, data sensitivity, architectural patterns, region hints |
| 2 | **Architecture** | Selects the optimal AWS services for your use case, assigns each a tier (networking / compute / database / storage / messaging / monitoring), and explains why each was chosen |
| 3 | **Diagram** | Generates a Mermaid flowchart of the service connections |
| 4 | **Cost** | Fetches or estimates real AWS pricing for every service and produces a line-item monthly cost breakdown |
| 5 | **Security** | Reviews the architecture for IAM, network, encryption, and compliance risks; outputs prioritised recommendations (critical / high / medium / low) |
| 6 | **Terraform** | Writes production-grade Terraform HCL for the entire architecture, ready to `terraform apply` |

The LangGraph `StateGraph` passes a shared `GraphState` TypedDict through each node so every agent can see everything produced before it.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| AI orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM | Amazon Bedrock (Claude via `langchain-aws`) |
| API | FastAPI + Mangum (Lambda adapter) |
| Infrastructure | Terraform (AWS Lambda + API Gateway + S3 + IAM) |
| Frontend | Vanilla JS + Canvas 2D API (zero dependencies) |
| Deployment | AWS Lambda (container or zip), or local Uvicorn |

---

## Project structure

```
CloudArchitectAI/
├── app/
│   ├── agents/
│   │   ├── requirements.py   # Agent 1 — parse description
│   │   ├── architecture.py   # Agent 2 — select AWS services
│   │   ├── diagram.py        # Agent 3 — Mermaid diagram
│   │   ├── cost.py           # Agent 4 — pricing estimates
│   │   ├── security.py       # Agent 5 — security review
│   │   └── terraform.py      # Agent 6 — IaC generation
│   ├── static/
│   │   └── index.html        # Single-file frontend (canvas demo + form + results)
│   ├── config.py             # Environment / Bedrock config
│   ├── graph.py              # LangGraph StateGraph definition
│   ├── main.py               # FastAPI app + /architect endpoint
│   ├── models.py             # Pydantic models for all agent I/O
│   └── pricing.py           # AWS Pricing API helpers
├── infra/
│   ├── main.tf               # Lambda, API Gateway, S3, CloudWatch
│   ├── iam.tf                # Execution role + Bedrock permissions
│   ├── variables.tf
│   └── outputs.tf
├── tests/
├── main.py                   # Uvicorn entrypoint for local dev
├── Makefile                  # install / test / local / package / deploy
├── requirements.txt
└── .env.example
```

---

## Prerequisites

- Python 3.11+
- AWS account with **Amazon Bedrock** enabled and model access granted for your chosen Claude model
- AWS credentials configured (`aws configure` or IAM role)
- Terraform ≥ 1.5 (for cloud deployment only)

---

## Quickstart — run locally

```bash
# 1. Clone
git clone https://github.com/<your-org>/CloudArchitectAI.git
cd CloudArchitectAI

# 2. Install dependencies
make install

# 3. Configure environment
cp .env.example .env
# Edit .env — set AWS_REGION and optionally S3_BUCKET_NAME

# 4. Start the dev server
make local
# → http://localhost:8000
```

The UI is served at `/` and the API at `/architect`.

---

## API

### `POST /architect`

Runs the full 6-agent pipeline and returns the complete result in a single JSON response (~2 minutes).

**Request body**

```json
{
  "description": "A scalable e-commerce platform handling 10,000 concurrent users...",
  "constraints": "Budget under $500/month, must be HIPAA-compliant",
  "session_id": "optional-uuid"
}
```

**Response**

```json
{
  "session_id": "uuid",
  "generated_at": "2025-05-07T20:00:00Z",
  "description": "...",
  "requirements": {
    "use_case": "e-commerce",
    "scale": "large",
    "data_sensitivity": "internal",
    "primary_patterns": ["microservices", "event-driven"],
    "constraints": ["budget-500", "hipaa"],
    "suggested_regions": ["us-east-1"]
  },
  "architecture": {
    "pattern": "serverless-microservices",
    "description": "...",
    "services": [
      {
        "service_name": "Amazon API Gateway",
        "aws_service_id": "api-gateway",
        "purpose": "REST API entry point",
        "why_chosen": "Managed, scales to zero, native Lambda integration",
        "tier": "networking"
      }
    ]
  },
  "mermaid_diagram": "graph TD\n  ...",
  "cost_estimate": [
    {
      "service": "aws-lambda",
      "monthly_cost_usd": 45.00,
      "assumptions": "2M requests/month, 512MB, 300ms avg",
      "pricing_source": "aws_pricing_api"
    }
  ],
  "total_monthly_cost_usd": 287.50,
  "security_recommendations": [
    {
      "category": "iam",
      "recommendation": "Use least-privilege execution roles per Lambda function...",
      "priority": "critical"
    }
  ],
  "terraform_code": "terraform {\n  required_version = ...\n}",
  "generation_time_seconds": 118.4
}
```

### `GET /health`

Returns `{"status": "healthy"}`. Used by ALB/API Gateway health checks.

---

## Deploy to AWS

The `infra/` directory provisions:
- **AWS Lambda** function (Python 3.11 runtime)
- **API Gateway** (HTTP API, proxy integration)
- **S3 bucket** for result storage (versioned, encrypted, private)
- **CloudWatch** log group (14-day retention)
- **IAM** execution role with Bedrock, S3, and CloudWatch permissions

```bash
# Build the Lambda zip (requires Docker for linux/amd64 deps)
make package

# Deploy with Terraform
make deploy
```

Or individually:

```bash
# 1. Package
docker run --rm --platform linux/amd64 \
  -v $(PWD):/var/task \
  public.ecr.aws/sam/build-python3.11 \
  pip install -r requirements.txt -t package/
cp -r app package/
cd package && zip -r ../lambda.zip . && cd ..

# 2. Terraform
cd infra
terraform init
terraform apply
```

---

## Frontend

The entire UI is a single `app/static/index.html` file with zero external JS dependencies. It has three screens:

**Act 1 — Homepage**
- Left 60%: Live canvas animation of a demo AWS e-commerce architecture (pure Canvas 2D, animated data packets, node pulse, slow pan)
- Right 40%: Input form — description textarea, example prompts, constraints field, submit

**Act 2 — Agent Pipeline**
- Real-time agent progress cards with typewriter status text
- Elapsed timer and progress bar
- Live canvas preview on the right

**Act 3 — Results**
- Left sidebar: Service list grouped by tier with monthly costs
- Center: Interactive SVG architecture diagram — pan, zoom, click nodes
- Right panel: Per-service detail — purpose, cost breakdown, security findings, Terraform snippet
- Action bar: Download Terraform `.tf` · Copy JSON · New Architecture

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | Region for Bedrock and all provisioned resources |
| `S3_BUCKET_NAME` | `cloudarchitectai-results-dev` | S3 bucket for saving architecture results |

AWS credentials are resolved from the standard chain: IAM role → `~/.aws/credentials` → environment variables.

---

## Running tests

```bash
make test
# or
python3 -m pytest tests/ -v
```

---

## Example prompts

**E-commerce platform**
> A scalable e-commerce platform handling 10,000 concurrent users. Needs product catalog, shopping cart, order processing, payment integration, and real-time inventory updates. Must handle Black Friday traffic spikes.

**Real-time analytics**
> A real-time analytics platform ingesting IoT sensor data from 50,000 devices. Needs stream processing, anomaly detection, dashboards, and alerting. Data must be queryable within 5 seconds of ingestion.

**IoT pipeline**
> An IoT data pipeline for a smart building system with 2,000 sensors reporting temperature, humidity, and energy usage every 30 seconds. Needs device management, data storage, and REST API for mobile app.

**Healthcare API**
> A HIPAA-compliant healthcare API for electronic health records. Needs patient data management, appointment scheduling, lab results integration, and audit logging. Must support HL7 FHIR standards.

---

## License

MIT
