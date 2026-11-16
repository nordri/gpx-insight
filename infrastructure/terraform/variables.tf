variable "aws_region" {
  description = "AWS region for the ECR repository."
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "Name of the project and its ECR repository."
  type        = string
  default     = "gpx-insight"
}

variable "floci_endpoint" {
  description = "FloCI ECR API endpoint; leave empty to use real AWS endpoints."
  type        = string
  default     = ""
}

variable "force_delete_repository" {
  description = "Allow deleting a non-empty repository; enable only for disposable labs."
  type        = bool
  default     = false
}
