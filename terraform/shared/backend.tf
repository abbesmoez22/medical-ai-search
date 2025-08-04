# ============================================================================
# TERRAFORM BACKEND SETUP
# ============================================================================
# This creates the S3 bucket and DynamoDB table needed to store Terraform state
# Think of this as creating a secure filing cabinet for our infrastructure plans

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Create a unique S3 bucket to store our Terraform state files
# State files contain the current status of all our AWS resources
resource "aws_s3_bucket" "terraform_state" {
  # Add random suffix to ensure bucket name is globally unique
  bucket = "medical-ai-search-terraform-state-${random_id.bucket_suffix.hex}"

  tags = {
    Name        = "Medical AI Search Terraform State"
    Environment = "shared"
    Project     = "medical-ai-search"
    ManagedBy   = "terraform"
  }
}

# Generate random 4-byte ID for unique bucket naming
# This prevents conflicts if someone else uses the same bucket name
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Enable versioning - keeps history of state file changes
# This lets us recover if something goes wrong with our infrastructure
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Encrypt all state files for security
# State files contain sensitive information like database passwords
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"  # AWS managed encryption
    }
  }
}

# Block all public access to prevent accidental exposure
# State files should NEVER be publicly accessible
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true  # Block public ACLs
  block_public_policy     = true  # Block public bucket policies
  ignore_public_acls      = true  # Ignore existing public ACLs
  restrict_public_buckets = true  # Restrict public bucket policies
}

# DynamoDB table for state locking
# Prevents multiple people from running terraform at the same time
resource "aws_dynamodb_table" "terraform_locks" {
  name           = "medical-ai-search-terraform-locks"
  billing_mode   = "PAY_PER_REQUEST"  # Pay only when used
  hash_key       = "LockID"           # Primary key for lock records

  attribute {
    name = "LockID"
    type = "S"  # String type
  }

  tags = {
    Name        = "Medical AI Search Terraform State Locks"
    Environment = "shared"
    Project     = "medical-ai-search"
    ManagedBy   = "terraform"
  }
}

# Output individual values for the setup script
output "backend_bucket" {
  value       = aws_s3_bucket.terraform_state.id
  description = "S3 bucket name for Terraform state"
}

output "backend_region" {
  value       = data.aws_region.current.name
  description = "AWS region for Terraform state"
}

output "backend_dynamodb_table" {
  value       = aws_dynamodb_table.terraform_locks.name
  description = "DynamoDB table name for Terraform state locking"
}

# Keep the complex output for reference
output "backend_config" {
  value = {
    bucket         = aws_s3_bucket.terraform_state.id
    key            = "terraform.tfstate"
    region         = data.aws_region.current.name
    dynamodb_table = aws_dynamodb_table.terraform_locks.name
    encrypt        = true
  }
  description = "Complete backend configuration for Terraform state"
}

data "aws_region" "current" {} 