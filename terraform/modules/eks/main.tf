# ============================================================================
# EKS MODULE - KUBERNETES CLUSTER
# ============================================================================
# Creates a managed Kubernetes cluster where our applications will run
# Think of this as setting up an apartment building with a professional manager

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

# Create the main EKS cluster
# This is the Kubernetes control plane that manages all our containers
resource "aws_eks_cluster" "main" {
  name     = "${var.project_name}-${var.environment}-cluster"
  role_arn = var.cluster_role_arn  # IAM role that gives EKS permissions
  version  = var.eks_version       # Kubernetes version (e.g., 1.28)

  vpc_config {
    # Deploy across both private and public subnets for flexibility
    subnet_ids              = concat(var.private_subnet_ids, var.public_subnet_ids)
    endpoint_private_access = true   # Allow access from within VPC
    endpoint_public_access  = true   # Allow access from internet (with restrictions)
    public_access_cidrs     = var.cluster_endpoint_public_access_cidrs  # Who can access from internet
  }

  # Enable comprehensive logging for troubleshooting and security
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # Ensure IAM role exists before creating cluster
  # This prevents ordering issues during creation/destruction
  depends_on = [
    var.cluster_role_arn,
  ]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-eks-cluster"
    Type = "eks-cluster"
  })
}

# Get the cluster's OIDC certificate for secure authentication
# This enables our pods to securely assume AWS IAM roles
data "tls_certificate" "cluster" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

# Create OIDC Identity Provider
# This allows Kubernetes pods to authenticate with AWS services securely
resource "aws_iam_openid_connect_provider" "cluster" {
  client_id_list  = ["sts.amazonaws.com"]  # AWS STS service
  thumbprint_list = [data.tls_certificate.cluster.certificates[0].sha1_fingerprint]
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-eks-oidc"
    Type = "oidc-provider"
  })
}

# Security Group for additional rules
resource "aws_security_group" "cluster_additional" {
  name_prefix = "${var.project_name}-${var.environment}-eks-cluster-additional-"
  vpc_id      = var.vpc_id

  ingress {
    from_port = 443
    to_port   = 443
    protocol  = "tcp"
    cidr_blocks = [var.vpc_cidr_block]
    description = "HTTPS access from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-eks-cluster-additional-sg"
    Type = "security-group"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# EKS Node Groups
resource "aws_eks_node_group" "system" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-${var.environment}-system-nodes"
  node_role_arn   = var.node_group_role_arn
  subnet_ids      = var.private_subnet_ids

  capacity_type  = "ON_DEMAND"
  instance_types = var.node_group_instance_types.system

  scaling_config {
    desired_size = var.node_group_scaling.system.desired_size
    max_size     = var.node_group_scaling.system.max_size
    min_size     = var.node_group_scaling.system.min_size
  }

  update_config {
    max_unavailable = 1
  }

  # Kubernetes labels
  labels = {
    role = "system"
    environment = var.environment
  }

  # Kubernetes taints for system nodes
  taint {
    key    = "CriticalAddonsOnly"
    value  = "true"
    effect = "NO_SCHEDULE"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-system-node-group"
    Type = "eks-node-group"
    "k8s.io/cluster-autoscaler/${aws_eks_cluster.main.name}" = "owned"
    "k8s.io/cluster-autoscaler/enabled" = "true"
  })

  # Ensure that IAM Role permissions are created before and deleted after EKS Node Group handling.
  depends_on = [
    var.node_group_role_arn,
  ]
}

resource "aws_eks_node_group" "application" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-${var.environment}-application-nodes"
  node_role_arn   = var.node_group_role_arn
  subnet_ids      = var.private_subnet_ids

  capacity_type  = var.environment == "prod" ? "ON_DEMAND" : "SPOT"
  instance_types = var.node_group_instance_types.application

  scaling_config {
    desired_size = var.node_group_scaling.application.desired_size
    max_size     = var.node_group_scaling.application.max_size
    min_size     = var.node_group_scaling.application.min_size
  }

  update_config {
    max_unavailable = 2
  }

  # Kubernetes labels
  labels = {
    role = "application"
    environment = var.environment
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-application-node-group"
    Type = "eks-node-group"
    "k8s.io/cluster-autoscaler/${aws_eks_cluster.main.name}" = "owned"
    "k8s.io/cluster-autoscaler/enabled" = "true"
  })

  # Ensure that IAM Role permissions are created before and deleted after EKS Node Group handling.
  depends_on = [
    var.node_group_role_arn,
  ]
}

# EKS Add-ons
resource "aws_eks_addon" "vpc_cni" {
  cluster_name             = aws_eks_cluster.main.name
  addon_name               = "vpc-cni"
  addon_version            = var.addon_versions.vpc_cni
  resolve_conflicts        = "OVERWRITE"
  service_account_role_arn = var.node_group_role_arn

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-vpc-cni-addon"
    Type = "eks-addon"
  })
}

resource "aws_eks_addon" "coredns" {
  cluster_name      = aws_eks_cluster.main.name
  addon_name        = "coredns"
  addon_version     = var.addon_versions.coredns
  resolve_conflicts = "OVERWRITE"

  depends_on = [aws_eks_node_group.system]

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-coredns-addon"
    Type = "eks-addon"
  })
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name      = aws_eks_cluster.main.name
  addon_name        = "kube-proxy"
  addon_version     = var.addon_versions.kube_proxy
  resolve_conflicts = "OVERWRITE"

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-kube-proxy-addon"
    Type = "eks-addon"
  })
}

resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name             = aws_eks_cluster.main.name
  addon_name               = "aws-ebs-csi-driver"
  addon_version            = var.addon_versions.ebs_csi_driver
  resolve_conflicts        = "OVERWRITE"
  service_account_role_arn = var.ebs_csi_driver_role_arn

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-ebs-csi-driver-addon"
    Type = "eks-addon"
  })
}

# CloudWatch Log Group for EKS cluster logs
resource "aws_cloudwatch_log_group" "cluster" {
  name              = "/aws/eks/${aws_eks_cluster.main.name}/cluster"
  retention_in_days = var.log_retention_days

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-eks-cluster-logs"
    Type = "log-group"
  })
}

# ECR Repositories for container images
resource "aws_ecr_repository" "app_repos" {
  for_each = toset(var.ecr_repositories)
  
  name                 = "${var.project_name}-${var.environment}-${each.key}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-${each.key}-ecr"
    Type = "ecr-repository"
  })
}

# ECR Lifecycle Policies
resource "aws_ecr_lifecycle_policy" "app_repos" {
  for_each = aws_ecr_repository.app_repos

  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Delete untagged images older than 1 day"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 1
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
} 