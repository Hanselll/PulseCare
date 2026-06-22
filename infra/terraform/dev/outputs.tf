output "ecr_repository_urls" {
  description = "ECR repository URLs for PulseCare service images."
  value = {
    for service_name, repository in aws_ecr_repository.services :
    service_name => repository.repository_url
  }
}

output "ecr_repository_arns" {
  description = "ECR repository ARNs for IAM policies."
  value = {
    for service_name, repository in aws_ecr_repository.services :
    service_name => repository.arn
  }
}

output "infra_pipeline_name" {
  description = "Infrastructure CodePipeline name."
  value       = aws_codepipeline.infra.name
}

output "terraform_codebuild_project_names" {
  description = "Terraform CodeBuild project names."
  value = {
    plan  = aws_codebuild_project.terraform_plan.name
    apply = aws_codebuild_project.terraform_apply.name
  }
}

output "infra_pipeline_artifact_bucket" {
  description = "S3 artifact bucket for the infrastructure pipeline."
  value       = aws_s3_bucket.infra_pipeline_artifacts.bucket
}
