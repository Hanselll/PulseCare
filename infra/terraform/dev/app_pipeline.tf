resource "aws_codepipeline" "app" {
  name          = var.app_pipeline_name
  role_arn      = aws_iam_role.app_codepipeline.arn
  pipeline_type = "V2"

  depends_on = [
    aws_iam_role_policy.app_codepipeline
  ]

  artifact_store {
    location = aws_s3_bucket.app_pipeline_artifacts.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["SourceArtifact"]

      configuration = {
        ConnectionArn        = var.github_connection_arn
        FullRepositoryId     = var.github_repository
        BranchName           = var.github_branch
        OutputArtifactFormat = "CODE_ZIP"
      }
    }
  }

  stage {
    name = "BuildImages"

    action {
      name            = "BuildImages"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      version         = "1"
      input_artifacts = ["SourceArtifact"]

      configuration = {
        ProjectName = aws_codebuild_project.app_image_build.name
      }
    }
  }

  stage {
    name = "DeployToEKS"

    action {
      name            = "DeployToEKS"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      version         = "1"
      input_artifacts = ["SourceArtifact"]

      configuration = {
        ProjectName = aws_codebuild_project.app_eks_deploy.name
      }
    }
  }
}
