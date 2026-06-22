# PulseCare Dev Terraform

This directory is the first IaC slice for the PulseCare AWS learning environment.
It manages the existing ECR repositories and lifecycle policies.

## Resources

- `pulsecare-ingestion-service`
- `pulsecare-risk-scoring-service`
- `pulsecare-alert-service`
- `pulsecare-device-simulator`

This stack keeps the low-cost DevOps control plane available by default:

- Terraform S3 backend and DynamoDB lock table are bootstrapped outside this stack and should stay in place.
- ECR repositories are kept so image history and repository URLs remain stable.
- App and infra CodePipeline/CodeBuild resources are kept so the environment can be recreated quickly.
- The EKS runtime layer is optional and controlled by `enable_eks`.

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

- ECR repositories are configured with mutable tags because the current learning pipeline still pushes `latest`.
- Lifecycle policies expire untagged images and keep the most recent images to control storage cost.

## Runtime Cost Toggle

The expensive development runtime is the EKS layer:

- VPC
- public subnets
- internet gateway
- route table
- EKS cluster
- managed node group
- EKS cluster and node IAM roles
- EKS access entry for the app deploy CodeBuild role

It is disabled by default:

```hcl
enable_eks = false
```

With `enable_eks = false`, Terraform keeps the backend, ECR, CodeBuild, and CodePipeline resources, but does not create the EKS runtime.

To create or recreate the runtime from CloudShell:

```bash
cd ~/PulseCare/infra/terraform/dev
terraform init
terraform plan -var="enable_eks=true"
terraform apply -var="enable_eks=true"
```

After the cluster is ready, deploy the app and monitoring stack by running the app pipeline:

```bash
aws codepipeline start-pipeline-execution \
  --name pulsecare-ci-pipeline \
  --region us-east-1
```

To access the recreated cluster:

```bash
aws eks update-kubeconfig \
  --region us-east-1 \
  --name pulsecare-dev
```

To stop the runtime cost while keeping the pipelines and image repositories:

```bash
cd ~/PulseCare/infra/terraform/dev

kubectl delete namespace monitoring --ignore-not-found
kubectl delete namespace pulsecare-dev --ignore-not-found

terraform plan -var="enable_eks=false"
terraform apply -var="enable_eks=false"
```

The namespace deletion is important because the application and monitoring resources are installed by Helm through the app deploy pipeline, not by this Terraform stack. Removing them first gives Kubernetes a chance to clean up service load balancers and related runtime resources before EKS is deleted.

If an existing `eksctl` cluster named `pulsecare-dev` still exists, choose one path before using this Terraform-managed EKS layer:

```bash
eksctl delete cluster --name pulsecare-dev --region us-east-1
```

or import the existing cluster and its related resources into Terraform. For this learning environment, deleting the old `eksctl` cluster and recreating it through Terraform is simpler and more repeatable.

## Infra Pipeline

The Terraform CI/CD pipeline should use:

- `infra/terraform/dev/buildspec-plan.yml`
- `infra/terraform/dev/buildspec-apply.yml`

Recommended pipeline flow:

```text
Source
  -> TerraformPlan
  -> ManualApproval
  -> TerraformApply
```

The plan stage emits the Terraform working directory as an artifact, including `tfplan`.
The apply stage uses that plan artifact as its source and runs `terraform apply tfplan`.

This Terraform configuration now manages:

- Infra pipeline artifact bucket
- Terraform CodeBuild service role and inline policy
- Terraform plan/apply CodeBuild projects
- Infra CodePipeline service role and inline policy
- `pulsecare-infra-pipeline`

If any of these resources were already created manually, import them before `terraform apply`.
Typical import commands:

```bash
terraform import aws_s3_bucket.infra_pipeline_artifacts pulsecare-infra-pipeline-artifacts-967002976835-us-east-1
terraform import aws_s3_bucket_public_access_block.infra_pipeline_artifacts pulsecare-infra-pipeline-artifacts-967002976835-us-east-1
terraform import aws_s3_bucket_server_side_encryption_configuration.infra_pipeline_artifacts pulsecare-infra-pipeline-artifacts-967002976835-us-east-1
terraform import aws_s3_bucket_versioning.infra_pipeline_artifacts pulsecare-infra-pipeline-artifacts-967002976835-us-east-1

terraform import aws_iam_role.terraform_codebuild codebuild-pulsecare-terraform-service-role
terraform import aws_iam_role_policy.terraform_codebuild codebuild-pulsecare-terraform-service-role:PulseCareTerraformCodeBuildAccess

terraform import aws_codebuild_project.terraform_plan pulsecare-terraform-plan
terraform import aws_codebuild_project.terraform_apply pulsecare-terraform-apply

terraform import aws_iam_role.infra_codepipeline codepipeline-pulsecare-infra-service-role
terraform import aws_iam_role_policy.infra_codepipeline codepipeline-pulsecare-infra-service-role:PulseCareInfraCodePipelineAccess

terraform import aws_codepipeline.infra pulsecare-infra-pipeline
```

If the resources do not exist yet, skip the imports and let Terraform create them:

```bash
terraform plan
terraform apply
```

## App Pipeline Management

This Terraform configuration also manages the learning application pipeline:

- App pipeline artifact bucket
- Image build CodeBuild role and project
- EKS deploy CodeBuild role and project
- App CodePipeline role and pipeline
- EKS access entry for the deploy CodeBuild role

Expected app pipeline flow:

```text
Source
  -> BuildImages
  -> DeployToEKS
```

If the app resources already exist, import them before `terraform apply`.

Typical import commands:

```bash
terraform import aws_iam_role.app_image_codebuild codebuild-pulsecare-image-build-service-role
terraform import aws_iam_role_policy.app_image_codebuild codebuild-pulsecare-image-build-service-role:PulseCareImageCodeBuildAccess

terraform import aws_iam_role.app_deploy_codebuild codebuild-pulsecare-eks-deploy-service-role
terraform import aws_iam_role_policy.app_deploy_codebuild codebuild-pulsecare-eks-deploy-service-role:PulseCareEksDeployCodeBuildAccess

terraform import aws_codebuild_project.app_image_build pulsecare-image-build
terraform import aws_codebuild_project.app_eks_deploy pulsecare-eks-deploy

terraform import aws_iam_role.app_codepipeline codepipeline-pulsecare-app-service-role
terraform import aws_iam_role_policy.app_codepipeline codepipeline-pulsecare-app-service-role:PulseCareAppCodePipelineAccess

terraform import aws_codepipeline.app pulsecare-ci-pipeline
```

The app artifact bucket in Terraform is a clean target bucket:

```text
pulsecare-app-pipeline-artifacts-967002976835-us-east-1
```

If you already created it manually, import it:

```bash
terraform import aws_s3_bucket.app_pipeline_artifacts pulsecare-app-pipeline-artifacts-967002976835-us-east-1
terraform import aws_s3_bucket_public_access_block.app_pipeline_artifacts pulsecare-app-pipeline-artifacts-967002976835-us-east-1
terraform import aws_s3_bucket_server_side_encryption_configuration.app_pipeline_artifacts pulsecare-app-pipeline-artifacts-967002976835-us-east-1
terraform import aws_s3_bucket_versioning.app_pipeline_artifacts pulsecare-app-pipeline-artifacts-967002976835-us-east-1
```

If the bucket does not exist, Terraform can create it.

For EKS access, the deploy CodeBuild role is granted cluster-admin access through EKS access entries.
If that access entry was created manually, import it before applying:

```bash
terraform import aws_eks_access_entry.app_deploy_codebuild pulsecare-dev:arn:aws:iam::967002976835:role/codebuild-pulsecare-eks-deploy-service-role
terraform import aws_eks_access_policy_association.app_deploy_codebuild_admin pulsecare-dev#arn:aws:iam::967002976835:role/codebuild-pulsecare-eks-deploy-service-role#arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy
```

If imports fail because the resource does not exist, let Terraform create it.

Important: this step does not manage the EKS cluster or node group itself yet. It only grants the deploy CodeBuild role access to the existing cluster.
