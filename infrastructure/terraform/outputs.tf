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
