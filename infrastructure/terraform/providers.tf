provider "aws" {
  region = var.aws_region

  access_key = var.floci_endpoint == "" ? null : "test"
  secret_key = var.floci_endpoint == "" ? null : "test"

  skip_credentials_validation = var.floci_endpoint != ""
  skip_metadata_api_check     = var.floci_endpoint != ""
  skip_requesting_account_id  = var.floci_endpoint != ""

  endpoints {
    ecr            = var.floci_endpoint
    iam            = var.floci_endpoint
    lambda         = var.floci_endpoint
    cloudwatchlogs = var.floci_endpoint
    apigatewayv2   = var.floci_endpoint
  }
}
