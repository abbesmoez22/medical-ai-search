#!/bin/bash

# Medical AI Platform - Development Setup Script
# This script sets up the local development environment

set -e

echo "🏥 Medical AI Platform - Development Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    print_status "Checking Docker..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Check if Docker Compose is available
check_docker_compose() {
    print_status "Checking Docker Compose..."
    if ! command -v docker-compose > /dev/null 2>&1; then
        print_error "Docker Compose is not installed. Please install Docker Compose and try again."
        exit 1
    fi
    print_success "Docker Compose is available"
}

# Create environment files
setup_env_files() {
    print_status "Setting up environment files..."
    
    # Auth service environment
    if [ ! -f "services/auth/.env" ]; then
        print_status "Creating auth service .env file..."
        cp services/auth/env.example services/auth/.env
        print_success "Auth service .env file created"
    else
        print_warning "Auth service .env file already exists"
    fi
}

# Start infrastructure services
start_infrastructure() {
    print_status "Starting infrastructure services..."
    docker-compose -f docker-compose.dev.yml up -d postgres redis zookeeper kafka elasticsearch
    
    print_status "Waiting for services to be healthy..."
    sleep 10
    
    # Check service health
    print_status "Checking service health..."
    
    # PostgreSQL
    if docker-compose -f docker-compose.dev.yml exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        print_success "PostgreSQL is ready"
    else
        print_warning "PostgreSQL might not be ready yet"
    fi
    
    # Redis
    if docker-compose -f docker-compose.dev.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_success "Redis is ready"
    else
        print_warning "Redis might not be ready yet"
    fi
    
    # Kafka (this might take longer)
    print_status "Kafka might take a few more seconds to be ready..."
    sleep 5
}

# Build and start application services
start_services() {
    print_status "Building and starting application services..."
    docker-compose -f docker-compose.dev.yml up -d --build auth-service
    
    print_status "Waiting for services to start..."
    sleep 10
    
    # Check auth service health
    if curl -f http://localhost:8001/health > /dev/null 2>&1; then
        print_success "Auth service is ready"
    else
        print_warning "Auth service might not be ready yet"
    fi
}

# Display service URLs
show_urls() {
    echo ""
    print_success "🎉 Development environment is ready!"
    echo ""
    echo "Service URLs:"
    echo "============="
    echo "• Auth Service:      http://localhost:8001"
    echo "• Auth Service Docs: http://localhost:8001/docs"
    echo "• PostgreSQL:        localhost:5432 (user: postgres, pass: password)"
    echo "• Redis:             localhost:6379"
    echo "• Kafka:             localhost:9094"
    echo "• Elasticsearch:     http://localhost:9200"
    echo "• Kibana:            http://localhost:5601"
    echo "• Kong Gateway:      http://localhost:8000"
    echo "• Kong Admin:        http://localhost:8001"
    echo ""
    echo "Useful commands:"
    echo "==============="
    echo "• View logs:         docker-compose -f docker-compose.dev.yml logs -f"
    echo "• Stop services:     docker-compose -f docker-compose.dev.yml down"
    echo "• Restart service:   docker-compose -f docker-compose.dev.yml restart <service>"
    echo "• Shell into service: docker-compose -f docker-compose.dev.yml exec <service> /bin/bash"
    echo ""
}

# Main execution
main() {
    cd "$(dirname "$0")/.."
    
    check_docker
    check_docker_compose
    setup_env_files
    start_infrastructure
    start_services
    show_urls
}

# Run main function
main "$@"