resource "aws_codebuild_project" "terraform_plan" {
  name         = var.terraform_plan_project_name
  service_role = aws_iam_role.terraform_codebuild.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux-x86_64-standard:5.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = false
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = "infra/terraform/dev/buildspec-plan.yml"
  }
}

resource "aws_codebuild_project" "terraform_apply" {
  name         = var.terraform_apply_project_name
  service_role = aws_iam_role.terraform_codebuild.arn

  artifacts {
    type = "CODEPIPELINE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/amazonlinux-x86_64-standard:5.0"
    type                        = "LINUX_CONTAINER"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = false
  }

  source {
    type      = "CODEPIPELINE"
    buildspec = "buildspec-apply.yml"
  }
}
