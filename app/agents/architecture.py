import json
import boto3
from botocore.config import Config
from app.config import ARCHITECTURE_MODEL, AWS_REGION
from app.models import Architecture, AWSService


def _extract_json(text: str) -> str:
    """Strip markdown fences and extract the outermost JSON object."""
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]
    return text

_bedrock = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION,
    config=Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 2})
)

SYSTEM_PROMPT = """You are a principal AWS solutions architect designing enterprise production systems.
Your job is to produce FOCUSED, OPINIONATED architectures — not exhaustive lists.
Every service must earn its place. Prefer doing more with fewer services.

═══ HARD RULES ═══

1. SELECT 8–12 SERVICES. Quality beats quantity — every service must justify its cost.

2. PUBLIC-FACING APPS — MANDATORY networking stack (no exceptions):
   Route 53 → CloudFront → WAF → ALB → Compute
   - Route 53     : DNS with health checks and failover (tier: networking)
   - CloudFront   : CDN for latency, DDoS absorption, TLS termination (tier: networking)
   - WAF          : Web Application Firewall sits IN FRONT of ALB — it is ALWAYS tier: networking
   - Certificate Manager : TLS cert for CloudFront + ALB (tier: security)
   Internal-only apps may omit Route 53 + CloudFront + WAF if traffic never leaves VPC.

3. COMMIT TO ONE PRIMARY COMPUTE STRATEGY:
   - Container workloads  → ECS Fargate + ALB
     (APIs, microservices, long-running, lift-and-shift)
   - Serverless workloads → Lambda + API Gateway HTTP API
     (event-driven, short-lived, spiky/variable traffic)
   - ALLOWED exception: ECS Fargate (web tier) + Lambda (async background jobs triggered by SQS/EventBridge)
   - NEVER mix Lambda + API Gateway + ECS + ALB as co-equal web tiers simultaneously.

4. AUTHENTICATION — if needs_user_auth=true:
   - Always include Cognito (tier: security) for user pools + JWT
   - Do NOT add both Cognito and a custom auth service — pick one.

5. MESSAGING — max 2 services, only if async processing is genuinely required:
   - SQS        → DEFAULT for task queuing, job decoupling, async background work
   - SNS        → fan-out pub/sub notifications
   - EventBridge → cross-service event routing in microservices
   - Kinesis    → ONLY for >10,000 events/sec sustained streaming (IoT, clickstream, telemetry)
                  NEVER use Kinesis for typical web/API async workloads — use SQS instead.

6. DATABASES — primary store + ONE supporting store maximum:
   - Relational (transactions, SQL, ACID)   → Aurora PostgreSQL
   - High-throughput key-value / document   → DynamoDB
   - ElastiCache Redis  → ONLY if session management or sub-millisecond cache is explicitly stated
   - OpenSearch         → ONLY if full-text product/content search is explicitly stated

7. ALWAYS INCLUDE:
   - Secrets Manager  (credentials, API keys, DB passwords)
   - CloudWatch       (logs, metrics, alarms)
   - X-Ray            (distributed tracing — always pair with CloudWatch)
   - The primary database

8. NEVER INCLUDE unless explicitly required:
   - GuardDuty, Macie, Security Hub (security posture tools — implicit, not shown in app diagrams)
   - Step Functions (only for multi-step human-approval or complex saga orchestration workflows)
   - Global Accelerator, Transit Gateway (multi-region only)
   - Kinesis for workloads under 10k events/sec
   - ECR unless container images are being built/stored as part of the described system

═══ REQUEST FLOW (draw services in this logical order) ═══
For public-facing container apps:
  User → Route 53 → CloudFront → WAF → ALB → ECS Fargate → Database → CloudWatch/X-Ray

For serverless apps:
  User → Route 53 → CloudFront → API Gateway → Lambda → Database → CloudWatch/X-Ray

For internal apps without CDN:
  User → ALB → ECS Fargate → Database → CloudWatch

═══ WHY_CHOSEN FORMAT ═══
Must name one rejected alternative and explain the tradeoff in 1-2 sentences.
Example: "Chosen over RDS single-instance because Aurora auto-scales storage and provides
  multi-AZ failover without manual replica management."
Use single quotes inside strings — never double quotes.

═══ TIER ASSIGNMENT (use EXACTLY these values — WAF is ALWAYS networking) ═══
- networking : Route 53, CloudFront, ALB, API Gateway, WAF
- security   : Certificate Manager, Cognito, Secrets Manager, KMS, IAM
- compute    : Lambda, ECS Fargate, EC2, Step Functions
- messaging  : SQS, SNS, EventBridge, Kinesis
- database   : DynamoDB, RDS, Aurora, ElastiCache, OpenSearch, DocumentDB
- storage    : S3, EFS
- monitoring : CloudWatch, X-Ray, CloudTrail

Return ONLY valid JSON — no markdown, no explanation:
{
  "services": [
    {
      "service_name": "display name",
      "aws_service_id": "exact AWS service name",
      "purpose": "what it does in this architecture",
      "why_chosen": "why this over the named alternative in 1-2 sentences",
      "tier": "networking|security|compute|messaging|database|storage|monitoring"
    }
  ],
  "pattern": "serverless|microservices|event-driven|monolithic|hybrid",
  "description": "2-3 sentence architecture summary"
}"""


def run_architecture_agent(state: dict) -> dict:
    requirements = state["requirements"]

    # Pull enriched fields (with safe fallbacks for backward compatibility)
    compute_pref    = getattr(requirements, 'compute_preference', 'serverless')
    traffic         = getattr(requirements, 'traffic_pattern', 'steady')
    needs_search    = getattr(requirements, 'needs_search', False)
    needs_stream    = getattr(requirements, 'needs_realtime_streaming', False)
    needs_reldb     = getattr(requirements, 'needs_relational_db', False)
    is_public       = getattr(requirements, 'is_public_facing', True)
    needs_auth      = getattr(requirements, 'needs_user_auth', False)

    networking_guidance = (
        "MANDATORY: Include Route 53, CloudFront, WAF (tier=networking), Certificate Manager, and ALB in that request flow order."
        if is_public else
        "Internal app: omit Route 53, CloudFront, WAF. Use ALB as the entry point."
    )

    auth_guidance = (
        "REQUIRED: Include Cognito (tier=security) for user pools and JWT token issuance."
        if needs_auth else
        "No user authentication service needed — do NOT include Cognito."
    )

    db_guidance = (
        "Use Aurora PostgreSQL as the primary database (relational access patterns required)."
        if needs_reldb else
        "Prefer DynamoDB as the primary database unless relational patterns are needed."
    )

    compute_guidance = (
        "Use Lambda + API Gateway as the primary compute (serverless, event-driven)."
        if compute_pref == 'serverless' else
        "Use ECS Fargate + ALB as the primary compute (container, persistent workload)."
        if compute_pref == 'container' else
        "Choose the best compute strategy for the described workload."
    )

    user_content = f"""Design a production-worthy AWS architecture for these requirements.
Follow ALL hard rules — select 8-12 services, enforce the mandatory networking stack for public apps.

Use case:               {requirements.use_case}
Scale:                  {requirements.scale}
Data sensitivity:       {requirements.data_sensitivity}
Compute preference:     {compute_pref}
Traffic pattern:        {traffic}
Public-facing:          {is_public}
Needs user auth:        {needs_auth}
Needs full-text search: {needs_search}
Needs real-time stream: {needs_stream}
Needs relational DB:    {needs_reldb}
Patterns:               {', '.join(requirements.primary_patterns)}
Constraints:            {', '.join(requirements.constraints) if requirements.constraints else 'none'}
Region:                 {requirements.suggested_regions[0] if requirements.suggested_regions else 'us-east-1'}

Decision guidance (follow exactly):
1. Networking  : {networking_guidance}
2. Auth        : {auth_guidance}
3. Compute     : {compute_guidance}
4. Database    : {db_guidance}
5. Search      : {'Include OpenSearch for full-text search.' if needs_search else 'Do NOT include OpenSearch.'}
6. Streaming   : {'Include Kinesis Data Streams (>10k events/sec justified).' if needs_stream else 'Do NOT include Kinesis. Use SQS if async queuing is needed.'}
7. Monitoring  : Always include CloudWatch AND X-Ray together.
8. Secrets     : Always include Secrets Manager."""

    response = _bedrock.invoke_model(
        modelId=ARCHITECTURE_MODEL,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 6144,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_content}]
        })
    )

    body = json.loads(response["body"].read())
    raw = _extract_json(body["content"][0]["text"])

    data = json.loads(raw)
    services = [AWSService(**s) for s in data["services"]]

    # Hard enforcement: replace any Kinesis with SQS when streaming wasn't requested
    if not needs_stream:
        cleaned = []
        kinesis_replaced = False
        for s in services:
            if 'kinesis' in (s.aws_service_id + s.service_name).lower() and not kinesis_replaced:
                cleaned.append(AWSService(
                    service_name='Amazon SQS',
                    aws_service_id='Amazon SQS',
                    purpose='Decoupled async task queue for background job processing',
                    why_chosen="Chosen over Kinesis Data Streams because this workload doesn't require high-throughput streaming; SQS delivers reliable at-least-once processing at a fraction of the cost.",
                    tier='messaging'
                ))
                kinesis_replaced = True
            else:
                cleaned.append(s)
        services = cleaned

    architecture = Architecture(
        services=services,
        pattern=data["pattern"],
        description=data["description"]
    )

    return {**state, "architecture": architecture, "current_agent": "diagram"}
