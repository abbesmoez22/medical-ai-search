output "documents_bucket_id" {
  description = "Documents bucket ID"
  value       = aws_s3_bucket.documents.id
}

output "documents_bucket_arn" {
  description = "Documents bucket ARN"
  value       = aws_s3_bucket.documents.arn
}

output "static_assets_bucket_id" {
  description = "Static assets bucket ID"
  value       = aws_s3_bucket.static_assets.id
}

output "static_assets_bucket_arn" {
  description = "Static assets bucket ARN"
  value       = aws_s3_bucket.static_assets.arn
}

output "ml_artifacts_bucket_id" {
  description = "ML artifacts bucket ID"
  value       = aws_s3_bucket.ml_artifacts.id
}

output "ml_artifacts_bucket_arn" {
  description = "ML artifacts bucket ARN"
  value       = aws_s3_bucket.ml_artifacts.arn
}

output "logs_bucket_id" {
  description = "Logs bucket ID"
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_arn" {
  description = "Logs bucket ARN"
  value       = aws_s3_bucket.logs.arn
}

output "backups_bucket_id" {
  description = "Backups bucket ID"
  value       = aws_s3_bucket.backups.id
}

output "backups_bucket_arn" {
  description = "Backups bucket ARN"
  value       = aws_s3_bucket.backups.arn
}

output "bucket_names" {
  description = "Map of all bucket names"
  value = {
    documents     = aws_s3_bucket.documents.id
    static_assets = aws_s3_bucket.static_assets.id
    ml_artifacts  = aws_s3_bucket.ml_artifacts.id
    logs          = aws_s3_bucket.logs.id
    backups       = aws_s3_bucket.backups.id
  }
} 