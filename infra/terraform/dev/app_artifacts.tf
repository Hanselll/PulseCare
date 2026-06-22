resource "aws_s3_bucket" "app_pipeline_artifacts" {
  bucket = var.app_pipeline_artifact_bucket_name
}

resource "aws_s3_bucket_public_access_block" "app_pipeline_artifacts" {
  bucket = aws_s3_bucket.app_pipeline_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "app_pipeline_artifacts" {
  bucket = aws_s3_bucket.app_pipeline_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "app_pipeline_artifacts" {
  bucket = aws_s3_bucket.app_pipeline_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}
