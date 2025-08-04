# ============================================================================
# DEVELOPMENT ENVIRONMENT - FULL INFRASTRUCTURE
# ============================================================================
# Complete infrastructure with VPC, EKS, RDS, Redis, and S3

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

  backend "s3" {
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "medical-ai-search-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(var.common_tags, {
      Environment = var.environment
    })
  }
}

# Generate Redis auth token
resource "random_password" "redis_auth_token" {
  length  = 32
  special = false
}

locals {
  environment = "dev"
  
  # Development-specific overrides
  node_group_scaling = {
    system = {
      desired_size = 1
      max_size     = 3
      min_size     = 1
    }
    application = {
      desired_size = 1
      max_size     = 3
      min_size     = 1
    }
  }
}

# ============================================================================
# INFRASTRUCTURE MODULES
# ============================================================================

# 1. VPC Module - Network foundation
module "vpc" {
  source = "../../modules/vpc"

  project_name             = var.project_name
  environment              = local.environment
  vpc_cidr                = var.vpc_cidr
  public_subnet_cidrs     = var.public_subnet_cidrs
  private_subnet_cidrs    = var.private_subnet_cidrs
  database_subnet_cidrs   = var.database_subnet_cidrs
  log_retention_days      = var.log_retention_days
  common_tags             = var.common_tags
}

# 2. Basic IAM Roles (without complex OIDC dependencies for now)
resource "aws_iam_role" "eks_cluster" {
  name = "${var.project_name}-${local.environment}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${local.environment}-eks-cluster-role"
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

resource "aws_iam_role" "eks_node_group" {
  name = "${var.project_name}-${local.environment}-eks-node-group-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${local.environment}-eks-node-group-role"
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node_group.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node_group.name
}

resource "aws_iam_role_policy_attachment" "eks_container_registry_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node_group.name
}

# 3. EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = "${var.project_name}-${local.environment}-cluster"
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.eks_version

  vpc_config {
    subnet_ids              = concat(module.vpc.private_subnet_ids, module.vpc.public_subnet_ids)
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  enabled_cluster_log_types = ["api", "audit"]

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${local.environment}-eks-cluster"
  })
}

# 4. EKS Node Group
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-${local.environment}-node-group"
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = module.vpc.private_subnet_ids

  capacity_type  = "ON_DEMAND"
  instance_types = var.node_group_instance_types.application

  scaling_config {
    desired_size = local.node_group_scaling.application.desired_size
    max_size     = local.node_group_scaling.application.max_size
    min_size     = local.node_group_scaling.application.min_size
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_container_registry_policy,
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${local.environment}-node-group"
  })
}

# 5. RDS Module - PostgreSQL database
module "rds" {
  source = "../../modules/rds"

  project_name              = var.project_name
  environment               = local.environment
  vpc_id                    = module.vpc.vpc_id
  database_subnet_ids       = module.vpc.database_subnet_ids
  allowed_security_groups   = [aws_eks_cluster.main.vpc_config[0].cluster_security_group_id]
  instance_class            = var.rds_instance_class
  allocated_storage         = var.rds_allocated_storage
  max_allocated_storage     = var.rds_max_allocated_storage
  multi_az                  = false # Single AZ for dev
  backup_retention_period   = 3     # Shorter retention for dev
  enable_monitoring         = false # Disabled for dev cost savings
  enable_deletion_protection = false # Allow deletion in dev
  create_read_replica       = false  # No read replica in dev
  common_tags               = var.common_tags

  depends_on = [module.vpc, aws_eks_cluster.main]
}

# 6. Redis Module - Cache
module "redis" {
  source = "../../modules/redis"

  project_name            = var.project_name
  environment             = local.environment
  vpc_id                  = module.vpc.vpc_id
  private_subnet_ids      = module.vpc.private_subnet_ids
  allowed_security_groups = [aws_eks_cluster.main.vpc_config[0].cluster_security_group_id]
  node_type               = var.redis_node_type
  num_cache_clusters      = 1 # Single node for dev
  auth_token              = random_password.redis_auth_token.result
  snapshot_retention_limit = 1 # Minimal retention for dev
  log_retention_days      = var.log_retention_days
  common_tags             = var.common_tags

  depends_on = [module.vpc, aws_eks_cluster.main]
}

# 7. S3 Module - Object storage
module "s3" {
  source = "../../modules/s3"

  project_name               = var.project_name
  environment                = local.environment
  cors_allowed_origins       = ["*"] # Open CORS for dev
  log_retention_days         = 90    # Shorter retention for dev
  enable_monitoring          = false # Disabled for dev cost savings
  bucket_size_alarm_threshold = 5368709120 # 5GB for dev
  common_tags                = var.common_tags
}

# ============================================================================
# MONITORING AND OUTPUTS
# ============================================================================

# Store important outputs in Parameter Store
resource "aws_ssm_parameter" "cluster_endpoint" {
  name  = "/${var.project_name}/${local.environment}/eks/cluster-endpoint"
  type  = "String"
  value = aws_eks_cluster.main.endpoint

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

# ============================================================================
# OUTPUTS
# ============================================================================

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = aws_eks_cluster.main.endpoint
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = module.rds.db_instance_endpoint
}

output "redis_primary_endpoint" {
  description = "Redis primary endpoint"
  value       = module.redis.redis_primary_endpoint
}

output "s3_buckets" {
  description = "S3 bucket names"
  value = {
    documents    = module.s3.documents_bucket_id
    static_assets = module.s3.static_assets_bucket_id
    ml_artifacts = module.s3.ml_artifacts_bucket_id
    logs         = module.s3.logs_bucket_id
    backups      = module.s3.backups_bucket_id
  }
}