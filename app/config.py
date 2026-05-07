import os

SONNET_MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
HAIKU_MODEL  = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

REQUIREMENTS_MODEL = HAIKU_MODEL
ARCHITECTURE_MODEL = SONNET_MODEL
DIAGRAM_MODEL      = HAIKU_MODEL
COST_MODEL         = HAIKU_MODEL
SECURITY_MODEL     = SONNET_MODEL
TERRAFORM_MODEL    = SONNET_MODEL

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET  = os.getenv("S3_BUCKET_NAME", "cloudarchitectai-results-dev")
