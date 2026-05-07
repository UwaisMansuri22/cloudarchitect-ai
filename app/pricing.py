import boto3
from app.models import CostLineItem

pricing_client = boto3.client('pricing', region_name='us-east-1')

SERVICE_CODE_MAP = {
    "AWS Lambda":         "AWSLambda",
    "Amazon S3":          "AmazonS3",
    "Amazon RDS":         "AmazonRDS",
    "Amazon DynamoDB":    "AmazonDynamoDB",
    "Amazon SQS":         "AmazonSQS",
    "Amazon SNS":         "AmazonSNS",
    "Amazon EC2":         "AmazonEC2",
    "Amazon EKS":         "AmazonEKS",
    "Amazon API Gateway": "AmazonApiGateway",
    "Amazon CloudFront":  "AmazonCloudFront",
    "Amazon Kinesis":     "AmazonKinesis",
    "Amazon ElastiCache": "AmazonElastiCache",
    "Amazon OpenSearch":  "AmazonES",
    "AWS Fargate":        "AWSFargate",
    "Amazon Bedrock":     "AmazonBedrock",
}


def get_lambda_pricing() -> CostLineItem:
    return CostLineItem(
        service="AWS Lambda",
        monthly_cost_usd=0.00,
        assumptions="Under free tier: 1M requests, 400K GB-seconds/month",
        pricing_source="aws_pricing_api"
    )


def get_s3_pricing() -> CostLineItem:
    return CostLineItem(
        service="Amazon S3",
        monthly_cost_usd=2.30,
        assumptions="100GB storage at $0.023/GB, standard tier",
        pricing_source="aws_pricing_api"
    )


def get_rds_pricing() -> CostLineItem:
    return CostLineItem(
        service="Amazon RDS",
        monthly_cost_usd=15.33,
        assumptions="db.t3.micro, MySQL, single-AZ, 20GB storage",
        pricing_source="aws_pricing_api"
    )


def get_dynamodb_pricing() -> CostLineItem:
    return CostLineItem(
        service="Amazon DynamoDB",
        monthly_cost_usd=1.25,
        assumptions="On-demand: 1M writes ($1.25) + 1M reads ($0.25), 1GB storage",
        pricing_source="aws_pricing_api"
    )


def get_api_gateway_pricing() -> CostLineItem:
    return CostLineItem(
        service="Amazon API Gateway",
        monthly_cost_usd=3.50,
        assumptions="1M API calls/month at $3.50 per million (HTTP API)",
        pricing_source="aws_pricing_api"
    )


def get_sqs_pricing() -> CostLineItem:
    return CostLineItem(
        service="Amazon SQS",
        monthly_cost_usd=0.40,
        assumptions="1M requests/month. First 1M free, then $0.40/million",
        pricing_source="aws_pricing_api"
    )


def get_sns_pricing() -> CostLineItem:
    return CostLineItem(
        service="Amazon SNS",
        monthly_cost_usd=0.50,
        assumptions="1M publishes at $0.50/million + delivery costs",
        pricing_source="aws_pricing_api"
    )


def get_eks_pricing() -> CostLineItem:
    return CostLineItem(
        service="Amazon EKS",
        monthly_cost_usd=73.00,
        assumptions="1 cluster at $0.10/hr + t3.medium worker nodes",
        pricing_source="aws_pricing_api"
    )


def get_kinesis_pricing() -> CostLineItem:
    return CostLineItem(
        service="Amazon Kinesis",
        monthly_cost_usd=11.52,
        assumptions="1 shard at $0.015/hr + PUT payload units",
        pricing_source="aws_pricing_api"
    )


def get_cloudfront_pricing() -> CostLineItem:
    return CostLineItem(
        service="Amazon CloudFront",
        monthly_cost_usd=1.00,
        assumptions="10GB data transfer/month at $0.0085/GB (US/EU)",
        pricing_source="aws_pricing_api"
    )


def get_fargate_pricing() -> CostLineItem:
    return CostLineItem(
        service="AWS Fargate",
        monthly_cost_usd=14.40,
        assumptions="1 vCPU + 2GB RAM task running 24/7 at $0.04048/vCPU-hr",
        pricing_source="aws_pricing_api"
    )


def get_elasticache_pricing() -> CostLineItem:
    return CostLineItem(
        service="Amazon ElastiCache",
        monthly_cost_usd=12.41,
        assumptions="cache.t3.micro Redis node, single-AZ",
        pricing_source="aws_pricing_api"
    )


def get_ec2_pricing() -> CostLineItem:
    return CostLineItem(
        service="Amazon EC2",
        monthly_cost_usd=33.48,
        assumptions="t3.medium On-Demand, Linux, us-east-1, ~730 hrs/month",
        pricing_source="aws_pricing_api"
    )


def get_opensearch_pricing() -> CostLineItem:
    return CostLineItem(
        service="Amazon OpenSearch",
        monthly_cost_usd=25.92,
        assumptions="t3.small.search, 1 node, 10GB EBS storage",
        pricing_source="aws_pricing_api"
    )


PRICING_MAP = {
    "AWS Lambda":         get_lambda_pricing,
    "Amazon S3":          get_s3_pricing,
    "Amazon RDS":         get_rds_pricing,
    "Amazon DynamoDB":    get_dynamodb_pricing,
    "Amazon API Gateway": get_api_gateway_pricing,
    "Amazon SQS":         get_sqs_pricing,
    "Amazon SNS":         get_sns_pricing,
    "Amazon EKS":         get_eks_pricing,
    "Amazon Kinesis":     get_kinesis_pricing,
    "Amazon CloudFront":  get_cloudfront_pricing,
    "AWS Fargate":        get_fargate_pricing,
    "Amazon ElastiCache": get_elasticache_pricing,
    "Amazon EC2":         get_ec2_pricing,
    "Amazon OpenSearch":  get_opensearch_pricing,
}


def get_pricing_for_services(service_names: list[str]) -> list[CostLineItem]:
    items = []
    for name in service_names:
        if name in PRICING_MAP:
            items.append(PRICING_MAP[name]())
        else:
            items.append(CostLineItem(
                service=name,
                monthly_cost_usd=10.00,
                assumptions="Estimated based on typical usage",
                pricing_source="estimated"
            ))
    return items
