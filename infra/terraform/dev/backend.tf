terraform {
  backend "s3" {
    bucket         = "pulsecare-terraform-state-967002976835-us-east-1"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "pulsecare-terraform-locks"
    encrypt        = true
  }
}
