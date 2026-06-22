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

## Remote State Bootstrap

Create the S3 backend bucket and DynamoDB lock table once per AWS account/region:

```bash
aws s3api create-bucket \
  --bucket pulsecare-terraform-state-967002976835-us-east-1 \
  --region us-east-1

aws s3api put-bucket-versioning \
  --bucket pulsecare-terraform-state-967002976835-us-east-1 \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket pulsecare-terraform-state-967002976835-us-east-1 \
  --server-side-encryption-configuration '{
    "Rules": [
      {
        "ApplyServerSideEncryptionByDefault": {
          "SSEAlgorithm": "AES256"
        }
      }
    ]
  }'

aws s3api put-public-access-block \
  --bucket pulsecare-terraform-state-967002976835-us-east-1 \
  --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws dynamodb create-table \
  --table-name pulsecare-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

After `backend.tf` is present and the bootstrap resources exist, migrate local state:

```bash
terraform init -migrate-state
terraform plan
```

## Notes

- This first IaC step deliberately does not manage EKS, IAM, or CodePipeline yet.
- ECR repositories are configured with mutable tags because the current learning pipeline still pushes `latest`.
- Lifecycle policies expire untagged images and keep the most recent images to control storage cost.
