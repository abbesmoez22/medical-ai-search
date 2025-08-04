variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "eks_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.28"
}

variable "vpc_id" {
  description = "VPC ID where EKS cluster will be created"
  type        = string
}

variable "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}

variable "cluster_role_arn" {
  description = "ARN of the EKS cluster IAM role"
  type        = string
}

variable "node_group_role_arn" {
  description = "ARN of the EKS node group IAM role"
  type        = string
}

variable "ebs_csi_driver_role_arn" {
  description = "ARN of the EBS CSI driver IAM role"
  type        = string
}

variable "node_group_instance_types" {
  description = "Instance types for EKS node groups"
  type        = map(list(string))
  default = {
    system      = ["t3.medium"]
    application = ["m5.large", "m5.xlarge"]
  }
}

variable "node_group_scaling" {
  description = "Scaling configuration for node groups"
  type = map(object({
    desired_size = number
    max_size     = number
    min_size     = number
  }))
  default = {
    system = {
      desired_size = 2
      max_size     = 4
      min_size     = 2
    }
    application = {
      desired_size = 3
      max_size     = 10
      min_size     = 2
    }
  }
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "List of CIDR blocks that can access the EKS cluster endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "addon_versions" {
  description = "Versions of EKS add-ons"
  type = object({
    vpc_cni        = string
    coredns        = string
    kube_proxy     = string
    ebs_csi_driver = string
  })
  default = {
    vpc_cni        = "v1.15.1-eksbuild.1"
    coredns        = "v1.10.1-eksbuild.4"
    kube_proxy     = "v1.28.2-eksbuild.2"
    ebs_csi_driver = "v1.24.0-eksbuild.1"
  }
}

variable "ecr_repositories" {
  description = "List of ECR repository names to create"
  type        = list(string)
  default = [
    "user-service",
    "search-service",
    "content-service",
    "ai-service",
    "analytics-service",
    "notification-service",
    "frontend"
  ]
}

variable "common_tags" {
  description = "Common tags to be applied to all resources"
  type        = map(string)
  default     = {}
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
} 