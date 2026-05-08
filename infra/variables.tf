variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "cloudarchitectai"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "lambda_memory_mb" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 1024
}

variable "lambda_timeout_seconds" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}

variable "s3_bucket_name" {
  description = "S3 bucket name for architecture results"
  type        = string
  default     = "cloudarchitectai-results-dev"
}

variable "daily_rate_limit" {
  description = "Max architecture requests per IP per day (0 = unlimited)"
  type        = number
  default     = 3
}
