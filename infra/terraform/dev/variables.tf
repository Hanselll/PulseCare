variable "aws_region" {
  description = "AWS region for PulseCare development resources."
  type        = string
  default     = "us-east-1"
}

variable "service_names" {
  description = "PulseCare service names that map to ECR repositories named pulsecare-<service>."
  type        = set(string)
  default = [
    "ingestion-service",
    "risk-scoring-service",
    "alert-service",
    "device-simulator",
  ]
}

variable "max_images" {
  description = "Maximum number of images to keep per ECR repository."
  type        = number
  default     = 10
}

variable "untagged_image_expire_days" {
  description = "Number of days before untagged ECR images expire."
  type        = number
  default     = 7
}
