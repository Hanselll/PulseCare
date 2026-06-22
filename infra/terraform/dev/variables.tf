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

variable "github_connection_arn" {
  description = "AWS CodeConnections ARN for the GitHub repository."
  type        = string
  default     = "arn:aws:codeconnections:us-east-1:967002976835:connection/19faabee-8f20-4446-8c54-ce733c823e61"
}

variable "github_repository" {
  description = "GitHub repository in owner/name form."
  type        = string
  default     = "Hanselll/PulseCare"
}

variable "github_branch" {
  description = "Git branch used by the infrastructure pipeline."
  type        = string
  default     = "main"
}

variable "terraform_state_bucket_name" {
  description = "S3 bucket name used by the Terraform backend."
  type        = string
  default     = "pulsecare-terraform-state-967002976835-us-east-1"
}

variable "terraform_lock_table_name" {
  description = "DynamoDB table name used by the Terraform backend lock."
  type        = string
  default     = "pulsecare-terraform-locks"
}

variable "infra_pipeline_artifact_bucket_name" {
  description = "S3 bucket name used for the infrastructure CodePipeline artifacts."
  type        = string
  default     = "pulsecare-infra-pipeline-artifacts-967002976835-us-east-1"
}

variable "terraform_codebuild_role_name" {
  description = "IAM role name for Terraform CodeBuild projects."
  type        = string
  default     = "codebuild-pulsecare-terraform-service-role"
}

variable "infra_codepipeline_role_name" {
  description = "IAM role name for the infrastructure CodePipeline."
  type        = string
  default     = "codepipeline-pulsecare-infra-service-role"
}

variable "terraform_plan_project_name" {
  description = "CodeBuild project name for Terraform plan."
  type        = string
  default     = "pulsecare-terraform-plan"
}

variable "terraform_apply_project_name" {
  description = "CodeBuild project name for Terraform apply."
  type        = string
  default     = "pulsecare-terraform-apply"
}

variable "infra_pipeline_name" {
  description = "CodePipeline name for infrastructure changes."
  type        = string
  default     = "pulsecare-infra-pipeline"
}

variable "eks_cluster_name" {
  description = "Existing EKS cluster name used by the app deployment pipeline."
  type        = string
  default     = "pulsecare-dev"
}

variable "enable_eks" {
  description = "Whether Terraform should create the EKS runtime layer."
  type        = bool
  default     = false
}

variable "vpc_cidr_block" {
  description = "CIDR block for the PulseCare development VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "eks_version" {
  description = "EKS Kubernetes version."
  type        = string
  default     = "1.36"
}

variable "eks_cluster_role_name" {
  description = "IAM role name for the EKS cluster."
  type        = string
  default     = "pulsecare-dev-eks-cluster-role"
}

variable "eks_node_role_name" {
  description = "IAM role name for the EKS managed node group."
  type        = string
  default     = "pulsecare-dev-eks-node-role"
}

variable "eks_node_group_name" {
  description = "EKS managed node group name."
  type        = string
  default     = "pulsecare-dev-ng"
}

variable "eks_node_instance_type" {
  description = "EC2 instance type for EKS worker nodes."
  type        = string
  default     = "t3.medium"
}

variable "eks_node_min_size" {
  description = "Minimum EKS worker node count."
  type        = number
  default     = 1
}

variable "eks_node_desired_size" {
  description = "Desired EKS worker node count."
  type        = number
  default     = 1
}

variable "eks_node_max_size" {
  description = "Maximum EKS worker node count."
  type        = number
  default     = 2
}

variable "app_pipeline_artifact_bucket_name" {
  description = "S3 bucket name used for the application CodePipeline artifacts."
  type        = string
  default     = "pulsecare-app-pipeline-artifacts-967002976835-us-east-1"
}

variable "app_image_codebuild_role_name" {
  description = "IAM role name for the app image build CodeBuild project."
  type        = string
  default     = "codebuild-pulsecare-image-build-service-role"
}

variable "app_deploy_codebuild_role_name" {
  description = "IAM role name for the EKS deploy CodeBuild project."
  type        = string
  default     = "codebuild-pulsecare-eks-deploy-service-role"
}

variable "app_codepipeline_role_name" {
  description = "IAM role name for the application CodePipeline."
  type        = string
  default     = "codepipeline-pulsecare-app-service-role"
}

variable "app_image_build_project_name" {
  description = "CodeBuild project name for app image builds."
  type        = string
  default     = "pulsecare-image-build"
}

variable "app_eks_deploy_project_name" {
  description = "CodeBuild project name for app EKS deployment."
  type        = string
  default     = "pulsecare-eks-deploy"
}

variable "app_pipeline_name" {
  description = "Application CodePipeline name."
  type        = string
  default     = "pulsecare-ci-pipeline"
}
