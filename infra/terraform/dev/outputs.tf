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
