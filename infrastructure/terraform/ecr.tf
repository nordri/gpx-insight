resource "aws_ecr_repository" "gpx_insight" {
  name         = var.project_name
  force_delete = var.force_delete_repository
}
