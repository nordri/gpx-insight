data "aws_ecr_image" "gpx_insight" {
  repository_name = aws_ecr_repository.gpx_insight.name
  image_tag       = "1.1.0"
}

locals {
  lambda_image_uri = var.floci_endpoint == "" ? (
    "${aws_ecr_repository.gpx_insight.repository_url}@${data.aws_ecr_image.gpx_insight.image_digest}"
    ) : (
    "127.0.0.1:${split(":", trimprefix(var.floci_endpoint, "http://"))[1]}/${split(".", aws_ecr_repository.gpx_insight.repository_url)[0]}/${var.aws_region}/${aws_ecr_repository.gpx_insight.name}@${data.aws_ecr_image.gpx_insight.image_digest}"
  )
}

resource "aws_iam_role" "lambda_execution" {
  name = "gpx-insight-lambda-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/gpx-insight"
  retention_in_days = 14
}

resource "aws_iam_role_policy" "lambda_logs" {
  name = "gpx-insight-lambda-logs"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
      ]
      Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
    }]
  })
}

resource "aws_lambda_function" "gpx_insight" {
  function_name = "gpx-insight"
  package_type  = "Image"
  image_uri     = local.lambda_image_uri
  role          = aws_iam_role.lambda_execution.arn
  memory_size   = 1024
  timeout       = 25
  architectures = ["x86_64"]

  image_config {}

  environment {
    variables = {
      GPX_MAX_SIZE_BYTES = "5242880"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.lambda_logs,
  ]
}
