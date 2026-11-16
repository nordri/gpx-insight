output "repository_url" {
  description = "ECR repository URI, including the registry host."
  value       = aws_ecr_repository.gpx_insight.repository_url
}

output "repository_name" {
  description = "ECR repository name."
  value       = aws_ecr_repository.gpx_insight.name
}

output "aws_region" {
  description = "AWS region configured for the repository."
  value       = var.aws_region
}

output "lambda_function_name" {
  description = "Name of the GPX Insight Lambda function."
  value       = aws_lambda_function.gpx_insight.function_name
}

output "lambda_function_arn" {
  description = "ARN of the GPX Insight Lambda function."
  value       = aws_lambda_function.gpx_insight.arn
}

output "lambda_image_uri" {
  description = "Immutable ECR image URI used by the Lambda function."
  value       = aws_lambda_function.gpx_insight.image_uri
}
