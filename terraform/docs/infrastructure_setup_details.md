# Cursor Agent Prompt: OpenEvidence Clone Infrastructure Setup

## Project Context
You are helping build an enterprise-grade medical AI search platform (OpenEvidence clone) designed for FAANG-level interview preparation. This is Phase 1 of a 3-month project focusing on **Foundation & Core Services - Infrastructure Setup**.

## Your Role
Act as a senior DevOps/Cloud engineer helping set up production-ready infrastructure. Prioritize enterprise patterns, best practices, and technologies that demonstrate mastery of modern cloud-native systems.

## Phase 1 Goals (Weeks 1-2)
Set up complete AWS infrastructure using Terraform with enterprise-grade patterns that showcase distributed systems expertise for technical interviews.

---

## Infrastructure Requirements

### AWS Architecture Overview
- **Multi-AZ deployment** for high availability
- **EKS cluster** with managed node groups
- **VPC** with public/private subnets
- **RDS PostgreSQL** with read replicas
- **ElastiCache Redis** cluster
- **Application Load Balancer** with SSL termination
- **S3 buckets** for document storage and static assets
- **CloudWatch** for monitoring and logging
- **IAM roles** following least privilege principle

### Terraform Structure
Create a **modular Terraform architecture** with:
```
terraform/
├── environments/
│   ├── dev/
│   ├── staging/
│   └── prod/
├── modules/
│   ├── vpc/
│   ├── eks/
│   ├── rds/
│   ├── redis/
│   ├── s3/
│   └── iam/
├── shared/
│   ├── backend.tf
│   └── variables.tf
└── scripts/
    └── setup.sh
```

### Key Enterprise Patterns to Implement
1. **Remote State Management**: S3 backend with DynamoDB locking
2. **Environment Separation**: Dev/Staging/Prod with identical configs
3. **Security Groups**: Principle of least access
4. **Tagging Strategy**: Cost allocation and resource management
5. **Secret Management**: AWS Secrets Manager integration
6. **Network Segmentation**: Public/private subnets with NAT Gateway

---

## Detailed Infrastructure Components

### 1. VPC & Networking
**Requirements:**
- Multi-AZ VPC (3 availability zones)
- Public subnets for load balancers
- Private subnets for application workloads
- Database subnets for RDS
- NAT Gateway for outbound internet access
- Internet Gateway for public access
- Route tables with proper routing
- Network ACLs for additional security

**Key Considerations:**
- CIDR blocks that don't overlap with corporate networks
- VPC Flow Logs for network monitoring
- VPC Endpoints for AWS services (reduce NAT costs)

### 2. EKS Cluster
**Requirements:**
- Managed EKS cluster (latest stable version)
- Managed node groups with mixed instance types
- Cluster autoscaler configuration
- AWS Load Balancer Controller
- EBS CSI driver for persistent volumes
- Cluster logging enabled (API, audit, authenticator)
- RBAC configuration

**Node Groups:**
- **System nodes**: t3.medium (2-4 nodes) for system pods
- **Application nodes**: m5.large (2-6 nodes, auto-scaling)
- **Spot instances** for cost optimization in non-prod

### 3. RDS PostgreSQL
**Requirements:**
- Multi-AZ deployment for high availability
- Read replicas for read scaling
- Automated backups with point-in-time recovery
- Parameter groups for performance tuning
- Subnet groups in private subnets
- Security groups for database access
- Enhanced monitoring enabled
- Encryption at rest and in transit

**Configuration:**
- Instance class: db.r5.large (production-ready)
- Storage: GP3 with encryption
- Backup retention: 7 days
- Maintenance window during low traffic

### 4. ElastiCache Redis
**Requirements:**
- Redis cluster mode enabled
- Multi-AZ with automatic failover
- Subnet groups in private subnets
- Parameter groups for optimization
- Security groups for application access
- Encryption in transit and at rest
- CloudWatch metrics integration

### 5. S3 Storage
**Buckets needed:**
- **Document storage**: Medical papers and files
- **Static assets**: Frontend builds and images
- **Terraform state**: Remote state storage
- **Logs**: Application and access logs
- **ML artifacts**: Models and training data

**Features:**
- Versioning enabled
- Server-side encryption (SSE-S3 or KMS)
- Lifecycle policies for cost optimization
- CORS configuration for frontend access
- CloudTrail logging for audit

### 6. Load Balancing & Ingress
**Requirements:**
- Application Load Balancer (ALB)
- SSL/TLS termination with ACM certificates
- AWS Load Balancer Controller in EKS
- Ingress configurations for services
- Health checks and target groups
- Route 53 for DNS management

---

## Security & Compliance Setup

### IAM Strategy
- **EKS Service Role**: Cluster management permissions
- **Node Group Role**: EC2, ECR, EKS worker permissions
- **Pod Roles**: IRSA (IAM Roles for Service Accounts)
- **Developer Roles**: Limited access with MFA
- **CI/CD Role**: Deployment permissions only

### Security Groups
- **ALB Security Group**: HTTP/HTTPS from internet
- **EKS Security Group**: API server access
- **Node Security Group**: Pod-to-pod communication
- **RDS Security Group**: Database access from EKS
- **Redis Security Group**: Cache access from EKS

### Secrets Management
- AWS Secrets Manager for database credentials
- External Secrets Operator in Kubernetes
- Encrypted parameter store for configuration
- Kubernetes secrets for service-to-service auth

---

## Monitoring & Observability Foundation

### CloudWatch Setup
- **Container Insights**: EKS cluster monitoring
- **RDS Enhanced Monitoring**: Database performance
- **VPC Flow Logs**: Network traffic analysis
- **Application Load Balancer logs**: Request analysis

### Log Aggregation
- **CloudWatch Log Groups**: Structured logging
- **Log retention policies**: Cost management
- **Log streaming**: Prepare for ELK stack integration

---

## Development Workflow Setup

### Local Development
- **kubectl** configuration for cluster access
- **AWS CLI** with proper profiles
- **Terraform** with workspace management
- **Docker** for local container builds
- **Helm** for Kubernetes package management

### CI/CD Preparation
- **ECR repositories**: Container image storage
- **GitHub Actions IAM role**: Deployment permissions
- **Terraform Cloud/AWS integration**: State management
- **Environment promotion strategy**: Dev → Staging → Prod

---

## Specific Tasks for Cursor Agent

### Priority 1: Core Infrastructure
1. **Create Terraform backend configuration** with S3 and DynamoDB
2. **Build VPC module** with all networking components
3. **Create EKS module** with proper node groups and add-ons
4. **Set up RDS module** with PostgreSQL and security
5. **Deploy ElastiCache module** with Redis cluster
6. **Configure S3 buckets** with proper policies and encryption

### Priority 2: Security & Access
1. **Implement IAM roles and policies** following least privilege
2. **Set up security groups** with minimal required access
3. **Configure AWS Secrets Manager** for sensitive data
4. **Enable CloudTrail** for audit logging
5. **Set up GuardDuty** for threat detection

### Priority 3: Monitoring Foundation
1. **Enable Container Insights** for EKS monitoring
2. **Set up CloudWatch dashboards** for key metrics
3. **Configure log groups** with retention policies
4. **Enable VPC Flow Logs** for network visibility

---

## Success Criteria

### Technical Validation
- [ ] Terraform plan/apply runs without errors
- [ ] EKS cluster accessible via kubectl
- [ ] RDS instance connects from EKS pods
- [ ] Redis cluster accessible from applications
- [ ] S3 buckets properly configured and accessible
- [ ] Load balancer routes traffic correctly
- [ ] All security groups follow least privilege
- [ ] Monitoring dashboards show cluster health

### Interview Readiness
- [ ] Can explain VPC design decisions
- [ ] Understand EKS networking and security
- [ ] Demonstrate infrastructure as code best practices
- [ ] Show cost optimization strategies
- [ ] Explain disaster recovery approach
- [ ] Showcase monitoring and observability

---

## Best Practices to Follow

### Terraform Standards
- Use consistent naming conventions
- Implement proper variable validation
- Add comprehensive documentation
- Use data sources where appropriate
- Implement resource tagging strategy
- Version pin all providers and modules

### Security Standards
- Enable encryption everywhere possible
- Use AWS Secrets Manager for credentials
- Implement network segmentation
- Follow AWS Well-Architected security pillar
- Enable logging for all services
- Use IAM roles instead of users where possible

### Cost Optimization
- Use spot instances for non-critical workloads
- Implement resource scheduling (dev environment shutdown)
- Set up billing alerts and cost monitoring
- Use appropriate instance sizing
- Implement S3 lifecycle policies
- Enable RDS automated backups optimization

---

## Expected Deliverables

1. **Working Terraform Infrastructure**: Complete AWS setup deployable to multiple environments
2. **Documentation**: Architecture diagrams and setup instructions
3. **Access Configuration**: kubectl and AWS CLI setup for development
4. **Monitoring Dashboards**: Basic CloudWatch visibility
5. **Security Baseline**: IAM, security groups, and encryption configured
6. **Cost Tracking**: Tagging and billing alerts in place

This infrastructure will serve as the foundation for the microservices, Kafka, and AI/ML components in subsequent phases. Focus on enterprise patterns and best practices that demonstrate production-ready thinking to technical interviewers.