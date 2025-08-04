output "eks_cluster_role_arn" {
  description = "ARN of the EKS cluster role"
  value       = aws_iam_role.eks_cluster.arn
}

output "eks_node_group_role_arn" {
  description = "ARN of the EKS node group role"
  value       = aws_iam_role.eks_node_group.arn
}

output "ebs_csi_driver_role_arn" {
  description = "ARN of the EBS CSI driver role"
  value       = aws_iam_role.ebs_csi_driver.arn
}

output "aws_load_balancer_controller_role_arn" {
  description = "ARN of the AWS Load Balancer Controller role"
  value       = aws_iam_role.aws_load_balancer_controller.arn
}

output "cluster_autoscaler_role_arn" {
  description = "ARN of the Cluster Autoscaler role"
  value       = aws_iam_role.cluster_autoscaler.arn
}

output "app_s3_access_role_arn" {
  description = "ARN of the application S3 access role"
  value       = aws_iam_role.app_s3_access.arn
} 