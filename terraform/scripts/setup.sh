#!/bin/bash

# Medical AI Search Platform - Infrastructure Setup Script
set -e

# Check prerequisites
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

if ! command_exists aws || ! command_exists terraform || ! command_exists jq; then
    echo "Error: Required tools missing. Install: aws-cli, terraform, jq"
    exit 1
fi

if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "Error: AWS credentials not configured. Run: aws configure"
    exit 1
fi

PROJECT_NAME="medical-ai-search"
AWS_REGION=${AWS_REGION:-"us-east-1"}

# Parse arguments
ENVIRONMENT="dev"
BACKEND_ONLY=false
INFO_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --backend-only) BACKEND_ONLY=true; shift ;;
        --info) INFO_ONLY=true; shift ;;
        dev|staging|prod) ENVIRONMENT=$1; shift ;;
        *) echo "Usage: $0 [--backend-only|--info] [dev|staging|prod]"; exit 1 ;;
    esac
done

if [ "$BACKEND_ONLY" = false ] && [ "$INFO_ONLY" = false ] && [ -z "$ENVIRONMENT" ]; then
    echo "Error: Environment required (dev|staging|prod)"
    exit 1
fi

echo "Starting infrastructure setup..."

# Setup backend
if [ "$BACKEND_ONLY" = true ] || [ "$INFO_ONLY" = false ]; then
    echo "Setting up Terraform backend..."
    cd "$(dirname "$0")/../shared"
    terraform init
    terraform apply -auto-approve -var="environment=shared"
    
    BACKEND_BUCKET=$(terraform output -raw backend_bucket)
    BACKEND_REGION=$(terraform output -raw backend_region)
    BACKEND_DYNAMODB_TABLE=$(terraform output -raw backend_dynamodb_table)
    
    echo "Backend setup complete"
    
    if [ "$BACKEND_ONLY" = true ]; then
        exit 0
    fi
    
    cd - >/dev/null
fi

# Deploy environment or show info
if [ -n "$ENVIRONMENT" ]; then
    cd "$(dirname "$0")/../environments/$ENVIRONMENT"
    
    if [ "$INFO_ONLY" = true ]; then
        echo "=== Infrastructure Info ==="
        echo "Cluster: $(terraform output -raw cluster_name 2>/dev/null || echo 'Not deployed')"
        echo "RDS: $(terraform output -raw rds_endpoint 2>/dev/null || echo 'Not deployed')"
        echo "Redis: $(terraform output -raw redis_primary_endpoint 2>/dev/null || echo 'Not deployed')"
        exit 0
    fi
    
    echo "Deploying $ENVIRONMENT environment..."
    
    # Initialize with backend
    terraform init \
        -backend-config="bucket=$BACKEND_BUCKET" \
        -backend-config="region=$BACKEND_REGION" \
        -backend-config="dynamodb_table=$BACKEND_DYNAMODB_TABLE" \
        -backend-config="key=dev/terraform.tfstate"
    
    # Deploy
    terraform plan -out="$ENVIRONMENT.tfplan"
    echo "Proceeding with deployment..."
    terraform apply "$ENVIRONMENT.tfplan"
    
    # Configure kubectl
    CLUSTER_NAME=$(terraform output -raw cluster_name)
    aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME
    
    echo "Deployment complete!"
    echo "Cluster: $CLUSTER_NAME"
    echo "Run 'kubectl get nodes' to verify"
fi 