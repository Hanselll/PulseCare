# PulseCare Dev Terraform

This directory is the first IaC slice for the PulseCare AWS learning environment.
It manages the existing ECR repositories and lifecycle policies.

## Resources

- `pulsecare-ingestion-service`
- `pulsecare-risk-scoring-service`
- `pulsecare-alert-service`
- `pulsecare-device-simulator`

## First-Time Setup

Run from this directory in AWS CloudShell or another shell with AWS credentials:

```bash
terraform init
```

Import the existing ECR repositories before applying:

```bash
terraform import 'aws_ecr_repository.services["ingestion-service"]' pulsecare-ingestion-service
terraform import 'aws_ecr_repository.services["risk-scoring-service"]' pulsecare-risk-scoring-service
terraform import 'aws_ecr_repository.services["alert-service"]' pulsecare-alert-service
terraform import 'aws_ecr_repository.services["device-simulator"]' pulsecare-device-simulator
```

Then check the plan:

```bash
terraform plan
```

If the plan only adds lifecycle policies or harmless repository settings, apply it:

```bash
terraform apply
```

## Notes

- This first IaC step deliberately does not manage EKS, IAM, or CodePipeline yet.
- ECR repositories are configured with mutable tags because the current learning pipeline still pushes `latest`.
- Lifecycle policies expire untagged images and keep the most recent images to control storage cost.
