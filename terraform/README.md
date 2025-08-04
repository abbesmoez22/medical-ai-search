# Medical AI Search Platform - Infrastructure

This directory contains the complete AWS infrastructure setup for the Medical AI Search Platform using Terraform. The infrastructure is designed with enterprise-grade patterns, security best practices, and scalability in mind.

## 🏗️ Architecture Overview

The infrastructure includes:

- **Multi-AZ VPC** with public, private, and database subnets
- **EKS Cluster** with managed node groups and auto-scaling
- **RDS PostgreSQL** with multi-AZ deployment and read replicas
- **ElastiCache Redis** cluster with encryption and monitoring
- **S3 Buckets** for documents, static assets, ML artifacts, logs, and backups
- **IAM Roles** following least privilege principle with IRSA support
- **CloudWatch** monitoring, logging, and dashboards
- **ECR Repositories** for container images

## 📁 Directory Structure

```
terraform/
├── shared/                 # Terraform backend configuration
│   ├── backend.tf
│   └── variables.tf
├── modules/               # Reusable Terraform modules
│   ├── vpc/              # VPC and networking
│   ├── eks/              # EKS cluster and node groups
│   ├── rds/              # PostgreSQL database
│   ├── redis/            # ElastiCache Redis
│   ├── s3/               # S3 buckets and policies
│   └── iam/              # IAM roles and policies
├── environments/         # Environment-specific configurations
│   ├── dev/              # Development environment
│   ├── staging/          # Staging environment (template)
│   └── prod/             # Production environment (template)
└── scripts/
    └── setup.sh          # Automated deployment script
```

## 🚀 Quick Start

### Prerequisites

1. **AWS CLI** - [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
2. **Terraform** (>= 1.0) - [Installation Guide](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
3. **kubectl** - [Installation Guide](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
4. **jq** - For JSON processing in scripts
5. **AWS Credentials** configured (`aws configure`)

### Automated Deployment

The easiest way to deploy the infrastructure is using the provided setup script:

```bash
# Make script executable (if not already)
chmod +x terraform/scripts/setup.sh

# Deploy development environment
./terraform/scripts/setup.sh dev

# Deploy with options
./terraform/scripts/setup.sh --help
```

### Manual Deployment

If you prefer manual deployment:

#### 1. Setup Terraform Backend

```bash
cd terraform/shared
terraform init
terraform plan
terraform apply
```

#### 2. Deploy Environment

```bash
cd terraform/environments/dev

# Initialize with backend
terraform init \
  -backend-config="bucket=<backend-bucket-name>" \
  -backend-config="region=us-west-2" \
  -backend-config="dynamodb_table=medical-ai-search-terraform-locks"

# Plan and apply
terraform plan
terraform apply
```

#### 3. Configure kubectl

```bash
# Get cluster name from outputs
CLUSTER_NAME=$(terraform output -raw cluster_name)

# Configure kubectl
aws eks update-kubeconfig --region us-west-2 --name $CLUSTER_NAME

# Verify connection
kubectl get nodes
```

## 🔧 Configuration

### Environment Variables

Key variables that can be customized:

```hcl
# VPC Configuration
vpc_cidr = "10.0.0.0/16"
public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
private_subnet_cidrs = ["10.0.10.0/24", "10.0.20.0/24", "10.0.30.0/24"]

# EKS Configuration
eks_version = "1.28"
node_group_instance_types = {
  system      = ["t3.medium"]
  application = ["m5.large"]
}

# RDS Configuration
rds_instance_class = "db.r5.large"
rds_allocated_storage = 100

# Redis Configuration
redis_node_type = "cache.r6g.large"
redis_num_cache_clusters = 2
```

### Environment-Specific Configurations

Each environment has optimized configurations:

- **Development**: Smaller instances, single-AZ, minimal monitoring
- **Staging**: Production-like setup with cost optimizations
- **Production**: Full high-availability, monitoring, and security

## 🛡️ Security Features

### Network Security
- Private subnets for application workloads
- Database subnets isolated from application layer
- Security groups with minimal required access
- VPC Flow Logs for network monitoring

### Encryption
- RDS encryption at rest and in transit
- Redis encryption at rest and in transit
- S3 server-side encryption
- EKS secrets encryption

### Access Control
- IAM roles following least privilege principle
- Service accounts with IAM roles (IRSA)
- Secrets stored in AWS Secrets Manager
- MFA requirements for sensitive operations

## 📊 Monitoring & Observability

### CloudWatch Integration
- Container Insights for EKS monitoring
- RDS Enhanced Monitoring
- ElastiCache metrics and alarms
- Custom dashboards for key metrics

### Logging
- VPC Flow Logs
- EKS cluster logs (API, audit, authenticator)
- Application logs via CloudWatch Log Groups
- Centralized log aggregation

### Alerting
- CPU utilization alarms
- Memory usage monitoring
- Database connection tracking
- Storage space alerts

## 🔄 CI/CD Integration

### ECR Repositories
Pre-configured repositories for:
- `user-service`
- `search-service`
- `content-service`
- `ai-service`
- `analytics-service`
- `notification-service`
- `frontend`

### IAM Roles for CI/CD
- GitHub Actions integration roles
- Deployment permissions
- ECR push/pull access

## 💰 Cost Optimization

### Development Environment
- Spot instances for non-critical workloads
- Smaller instance sizes
- Reduced backup retention
- Minimal monitoring to reduce costs

### Production Environment
- Reserved instances for predictable workloads
- Auto-scaling based on demand
- S3 lifecycle policies for cost-effective storage
- Right-sized instances based on usage

## 🚨 Disaster Recovery

### Backup Strategy
- RDS automated backups with point-in-time recovery
- Redis snapshots
- S3 versioning and cross-region replication
- Infrastructure as Code for rapid recovery

### High Availability
- Multi-AZ deployments
- Auto-scaling groups
- Load balancing across availability zones
- Database read replicas

## 📋 Operations Guide

### Common Commands

```bash
# Check cluster status
kubectl get nodes
kubectl get pods --all-namespaces

# View infrastructure outputs
terraform output

# Access database credentials
aws secretsmanager get-secret-value --secret-id <secret-arn>

# Monitor resources
aws cloudwatch get-dashboard --dashboard-name <dashboard-name>
```

### Scaling Operations

```bash
# Scale node groups
aws eks update-nodegroup-config \
  --cluster-name <cluster-name> \
  --nodegroup-name <nodegroup-name> \
  --scaling-config minSize=2,maxSize=10,desiredSize=5

# Scale application pods
kubectl scale deployment <deployment-name> --replicas=5
```

### Maintenance Tasks

1. **Regular Updates**
   - EKS cluster version updates
   - Node group AMI updates
   - Security patches

2. **Monitoring**
   - Review CloudWatch dashboards
   - Check alarm status
   - Analyze cost reports

3. **Security**
   - Rotate secrets regularly
   - Review IAM permissions
   - Update security groups as needed

## 🔍 Troubleshooting

### Common Issues

1. **EKS Cluster Access Issues**
   ```bash
   # Update kubeconfig
   aws eks update-kubeconfig --region us-west-2 --name <cluster-name>
   
   # Check IAM permissions
   aws sts get-caller-identity
   ```

2. **Database Connection Issues**
   ```bash
   # Check security groups
   aws ec2 describe-security-groups --group-ids <sg-id>
   
   # Test connectivity from EKS
   kubectl run test-pod --image=postgres:15 --rm -it -- psql -h <rds-endpoint>
   ```

3. **Resource Limits**
   ```bash
   # Check resource quotas
   kubectl describe resourcequota
   
   # View node resources
   kubectl top nodes
   ```

### Support Resources

- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

## 🤝 Contributing

When making changes to the infrastructure:

1. Create a feature branch
2. Test changes in development environment
3. Update documentation
4. Submit pull request with detailed description
5. Ensure all tests pass before merging

## 📄 License

This infrastructure code is part of the Medical AI Search Platform project and follows the same licensing terms.

---

For questions or support, please contact the platform team or create an issue in the project repository. 