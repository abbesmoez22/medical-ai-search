# ============================================================================
# DEVELOPMENT ENVIRONMENT - MAIN ORCHESTRATION
# ============================================================================
# This file brings together all our infrastructure modules to create a complete
# development environment. Think of this as the blueprint that builds our entire
# cloud city by combining all the individual components.

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Configure remote state storage
  # This stores our infrastructure state in S3 for team collaboration
  backend "s3" {
    # Backend configuration provided during init by our setup script
    # terraform init -backend-config="bucket=your-terraform-state-bucket"
    key            = "dev/terraform.tfstate"    # Path within the bucket
    region         = "us-east-1"                # AWS region
    encrypt        = true                       # Encrypt state file
    dynamodb_table = "medical-ai-search-terraform-locks"  # Prevent concurrent runs
  }
}

# Configure the AWS provider with default tags
# All resources will automatically get these tags
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(var.common_tags, {
      Environment = var.environment
    })
  }
}

# Generate a secure authentication token for Redis
# This password protects our cache from unauthorized access
resource "random_password" "redis_auth_token" {
  length  = 32        # Long password for security
  special = false     # No special chars (Redis compatibility)
}

# Local configuration values specific to development environment
# These override the default values for cost optimization in dev
locals {
  environment = "dev"
  
  # Development-specific overrides
  node_group_scaling = {
    system = {
      desired_size = 2
      max_size     = 3
      min_size     = 1
    }
    application = {
      desired_size = 2
      max_size     = 5
      min_size     = 1
    }
  }
}

# ============================================================================
# MODULE CALLS - BUILDING OUR INFRASTRUCTURE
# ============================================================================
# Each module call below creates a specific part of our infrastructure
# Order matters: VPC first, then IAM, then services that depend on them

# 1. VPC Module - Build the network foundation
# Creates our private cloud network with subnets across multiple zones
module "vpc" {
  source = "../../modules/vpc"

  project_name             = var.project_name
  environment              = local.environment
  vpc_cidr                = var.vpc_cidr                    # Main network range (10.0.0.0/16)
  public_subnet_cidrs     = var.public_subnet_cidrs        # Internet-accessible subnets
  private_subnet_cidrs    = var.private_subnet_cidrs       # Application subnets
  database_subnet_cidrs   = var.database_subnet_cidrs      # Database-only subnets
  log_retention_days      = var.log_retention_days         # How long to keep logs
  common_tags             = var.common_tags
}

# 2. IAM Module - Set up security roles and permissions
# Creates all the IAM roles needed for EKS, applications, and AWS services
module "iam" {
  source = "../../modules/iam"

  project_name      = var.project_name
  environment       = local.environment
  oidc_provider_arn = module.eks.oidc_provider_arn         # From EKS for secure pod authentication
  oidc_provider_url = module.eks.oidc_provider_url         # From EKS for secure pod authentication
  common_tags       = var.common_tags

  depends_on = [module.eks]  # Wait for EKS to create OIDC provider first
}

# 3. EKS Module - Create the Kubernetes cluster
# Sets up our container orchestration platform where applications will run
module "eks" {
  source = "../../modules/eks"

  project_name               = var.project_name
  environment                = local.environment
  eks_version                = var.eks_version              # Kubernetes version
  vpc_id                     = module.vpc.vpc_id            # Use the VPC we created
  vpc_cidr_block            = module.vpc.vpc_cidr_block     # For security group rules
  private_subnet_ids        = module.vpc.private_subnet_ids # Where to place worker nodes
  public_subnet_ids         = module.vpc.public_subnet_ids  # For load balancers
  cluster_role_arn          = module.iam.eks_cluster_role_arn       # IAM role for cluster
  node_group_role_arn       = module.iam.eks_node_group_role_arn    # IAM role for nodes
  ebs_csi_driver_role_arn   = module.iam.ebs_csi_driver_role_arn    # IAM role for storage
  node_group_instance_types = var.node_group_instance_types         # EC2 instance types
  node_group_scaling        = local.node_group_scaling              # Auto-scaling config
  log_retention_days        = var.log_retention_days
  common_tags               = var.common_tags

  depends_on = [module.vpc, module.iam]
}

# RDS Module
module "rds" {
  source = "../../modules/rds"

  project_name              = var.project_name
  environment               = local.environment
  vpc_id                    = module.vpc.vpc_id
  database_subnet_ids       = module.vpc.database_subnet_ids
  allowed_security_groups   = [module.eks.cluster_security_group_id]
  instance_class            = var.rds_instance_class
  allocated_storage         = var.rds_allocated_storage
  max_allocated_storage     = var.rds_max_allocated_storage
  multi_az                  = false # Single AZ for dev
  backup_retention_period   = 3     # Shorter retention for dev
  enable_monitoring         = var.enable_monitoring
  enable_deletion_protection = false # Allow deletion in dev
  create_read_replica       = false  # No read replica in dev
  common_tags               = var.common_tags

  depends_on = [module.vpc, module.eks]
}

# Redis Module
module "redis" {
  source = "../../modules/redis"

  project_name            = var.project_name
  environment             = local.environment
  vpc_id                  = module.vpc.vpc_id
  private_subnet_ids      = module.vpc.private_subnet_ids
  allowed_security_groups = [module.eks.cluster_security_group_id]
  node_type               = var.redis_node_type
  num_cache_clusters      = 1 # Single node for dev
  auth_token              = random_password.redis_auth_token.result
  snapshot_retention_limit = 1 # Minimal retention for dev
  log_retention_days      = var.log_retention_days
  common_tags             = var.common_tags

  depends_on = [module.vpc, module.eks]
}

# S3 Module
module "s3" {
  source = "../../modules/s3"

  project_name               = var.project_name
  environment                = local.environment
  cors_allowed_origins       = ["*"] # Open CORS for dev
  log_retention_days         = 90    # Shorter retention for dev
  enable_monitoring          = var.enable_monitoring
  bucket_size_alarm_threshold = 5368709120 # 5GB for dev
  common_tags                = var.common_tags
}

# CloudWatch Dashboard for monitoring
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-${local.environment}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/EKS", "cluster_failed_request_count", "ClusterName", module.eks.cluster_name],
            ["AWS/EKS", "cluster_request_total", "ClusterName", module.eks.cluster_name]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "EKS Cluster Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", module.rds.db_instance_id],
            ["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", module.rds.db_instance_id]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "RDS Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", "CacheClusterId", "${module.redis.redis_replication_group_id}-001"],
            ["AWS/ElastiCache", "DatabaseMemoryUsagePercentage", "CacheClusterId", "${module.redis.redis_replication_group_id}-001"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Redis Metrics"
          period  = 300
        }
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${local.environment}-dashboard"
    Type = "cloudwatch-dashboard"
  })
}

# Store important outputs in Parameter Store for easy access
resource "aws_ssm_parameter" "cluster_endpoint" {
  name  = "/${var.project_name}/${local.environment}/eks/cluster-endpoint"
  type  = "String"
  value = module.eks.cluster_endpoint

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${local.environment}-cluster-endpoint"
    Type = "ssm-parameter"
  })
}

resource "aws_ssm_parameter" "rds_endpoint" {
  name  = "/${var.project_name}/${local.environment}/rds/endpoint"
  type  = "String"
  value = module.rds.db_instance_endpoint

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${local.environment}-rds-endpoint"
    Type = "ssm-parameter"
  })
}

resource "aws_ssm_parameter" "redis_endpoint" {
  name  = "/${var.project_name}/${local.environment}/redis/endpoint"
  type  = "String"
  value = module.redis.redis_primary_endpoint

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${local.environment}-redis-endpoint"
    Type = "ssm-parameter"
  })
} 