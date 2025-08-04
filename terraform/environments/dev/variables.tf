# ============================================================================
# DEVELOPMENT ENVIRONMENT VARIABLES
# ============================================================================
# These variables control how our infrastructure is configured
# Think of these as the settings panel for our cloud environment

# ============================================================================
# PROJECT BASICS
# ============================================================================

variable "project_name" {
  description = "Name of the project - used in all resource names"
  type        = string
  default     = "medical-ai-search"
}

variable "environment" {
  description = "Environment name (dev/staging/prod) - affects resource sizing"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region where all resources will be created"
  type        = string
  default     = "us-east-1"  # Virginia - good for US East Coast users
}

variable "availability_zones" {
  description = "List of availability zones for high availability"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]  # 3 zones in Virginia
}

# ============================================================================
# NETWORK CONFIGURATION
# ============================================================================
# IP address ranges for our different network segments
# Think of these as different neighborhoods in our cloud city

variable "vpc_cidr" {
  description = "Main IP range for our entire VPC (like the city limits)"
  type        = string
  default     = "10.0.0.0/16"  # Allows ~65,000 IP addresses
}

variable "public_subnet_cidrs" {
  description = "IP ranges for public subnets (internet-accessible)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]  # ~250 IPs each
}

variable "private_subnet_cidrs" {
  description = "IP ranges for private subnets (application servers)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24", "10.0.30.0/24"]  # ~250 IPs each
}

variable "database_subnet_cidrs" {
  description = "IP ranges for database subnets (databases only)"
  type        = list(string)
  default     = ["10.0.100.0/24", "10.0.101.0/24", "10.0.102.0/24"]  # ~250 IPs each
}

# EKS Configuration
variable "eks_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.28"
}

variable "node_group_instance_types" {
  description = "Instance types for EKS node groups"
  type        = map(list(string))
  default = {
    system      = ["t3.medium"]
    application = ["t3.large"]  # Smaller instances for dev
  }
}

# RDS Configuration (Dev-optimized)
variable "rds_instance_class" {
  description = "Instance class for RDS"
  type        = string
  default     = "db.t3.micro"  # Smaller instance for dev
}

variable "rds_allocated_storage" {
  description = "Allocated storage for RDS in GB"
  type        = number
  default     = 20  # Smaller storage for dev
}

variable "rds_max_allocated_storage" {
  description = "Maximum allocated storage for RDS in GB"
  type        = number
  default     = 100  # Lower max for dev
}

# ElastiCache Configuration (Dev-optimized)
variable "redis_node_type" {
  description = "Node type for ElastiCache Redis"
  type        = string
  default     = "cache.t3.micro"  # Smaller instance for dev
}

variable "redis_num_cache_clusters" {
  description = "Number of cache clusters for Redis"
  type        = number
  default     = 1  # Single node for dev
}

# Monitoring and Logging
variable "enable_monitoring" {
  description = "Enable enhanced monitoring"
  type        = bool
  default     = false  # Disabled for cost savings in dev
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7  # Shorter retention for dev
}

# Common Tags
variable "common_tags" {
  description = "Common tags to be applied to all resources"
  type        = map(string)
  default = {
    Project     = "medical-ai-search"
    Environment = "dev"
    ManagedBy   = "terraform"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
}

 