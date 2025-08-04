#!/bin/bash

# Medical AI Platform - Development Environment Setup
# This script sets up the complete Phase 2 backend development environment

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
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Check if Docker Compose is available
check_docker_compose() {
    print_status "Checking Docker Compose..."
    if ! command -v docker-compose >/dev/null 2>&1; then
        print_error "Docker Compose is not installed. Please install Docker Compose and try again."
        exit 1
    fi
    print_success "Docker Compose is available"
}

# Check for port conflicts
check_ports() {
    print_status "Checking for port conflicts..."
    
    PORTS=(5433 6380 9095 9201 8100 8102 8003 8010 8011 8013 8014 8015)
    CONFLICTS=()
    
    for port in "${PORTS[@]}"; do
        if lsof -i :$port >/dev/null 2>&1; then
            CONFLICTS+=($port)
        fi
    done
    
    if [ ${#CONFLICTS[@]} -ne 0 ]; then
        print_warning "Port conflicts detected on: ${CONFLICTS[*]}"
        print_warning "These ports are required for the services to run properly."
        print_warning "Please stop the conflicting services or change the port mappings."
        
        read -p "Do you want to continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "No port conflicts detected"
    fi
}

# Create environment files if they don't exist
setup_env_files() {
    print_status "Setting up environment files..."
    
    # Auth service
    if [ ! -f "./services/auth/.env" ]; then
        cp "./services/auth/env.example" "./services/auth/.env"
        print_success "Created auth service .env file"
    fi
    
    # Document management service
    if [ ! -f "./services/document-management/.env" ]; then
        cp "./services/document-management/env.example" "./services/document-management/.env"
        print_success "Created document management service .env file"
    fi
    
    # Content processing service
    if [ ! -f "./services/content-processing/.env" ]; then
        if [ -f "./services/content-processing/env.example" ]; then
            cp "./services/content-processing/env.example" "./services/content-processing/.env"
            print_success "Created content processing service .env file"
        fi
    fi
}

# Make initialization script executable
setup_permissions() {
    print_status "Setting up file permissions..."
    chmod +x ./infrastructure/postgres/init-multiple-databases.sh
    print_success "Database initialization script is executable"
}

# Start infrastructure services
start_infrastructure() {
    print_status "Starting infrastructure services..."
    
    # Start database and message queue services first
    docker-compose -f docker-compose.dev.yml up -d postgres redis zookeeper kafka elasticsearch kong-database kong-migration kong
    
    print_status "Waiting for infrastructure services to be healthy..."
    
    # Wait for services to be healthy (with timeout)
    local timeout=300  # 5 minutes
    local elapsed=0
    local interval=10
    
    while [ $elapsed -lt $timeout ]; do
        if docker-compose -f docker-compose.dev.yml ps | grep -q "healthy"; then
            local unhealthy=$(docker-compose -f docker-compose.dev.yml ps | grep -v "healthy" | grep -c "starting\|unhealthy" || echo "0")
            if [ "$unhealthy" -eq 0 ]; then
                break
            fi
        fi
        
        print_status "Waiting for services to be ready... (${elapsed}s/${timeout}s)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done
    
    if [ $elapsed -ge $timeout ]; then
        print_warning "Some infrastructure services may not be fully ready. Continuing anyway..."
    else
        print_success "Infrastructure services are ready"
    fi
}

# Start application services
start_applications() {
    print_status "Starting application services..."
    
    # Start application services
    docker-compose -f docker-compose.dev.yml up -d auth-service document-service processing-service
    
    print_status "Waiting for application services to start..."
    sleep 30
    
    # Check service health
    check_service_health
}

# Check service health
check_service_health() {
    print_status "Checking service health..."
    
    local services=("auth-service:8010" "document-service:8011" "processing-service:8013")
    local healthy_count=0
    
    for service_port in "${services[@]}"; do
        local service=$(echo $service_port | cut -d: -f1)
        local port=$(echo $service_port | cut -d: -f2)
        
        if curl -f -s "http://localhost:$port/health" >/dev/null 2>&1; then
            print_success "$service is healthy"
            healthy_count=$((healthy_count + 1))
        else
            print_warning "$service is not responding on port $port"
        fi
    done
    
    print_status "Health check complete: $healthy_count/${#services[@]} services healthy"
}

# Display service information
show_service_info() {
    echo
    echo "🎉 Development Environment Setup Complete!"
    echo "========================================"
    echo
    echo "📋 Service Information:"
    echo "----------------------"
    echo "🔐 Auth Service:           http://localhost:8010"
    echo "📄 Document Management:    http://localhost:8011"  
    echo "⚙️  Content Processing:     http://localhost:8013"
    echo "🔍 Search Indexing:        http://localhost:8014"
    echo "🔎 Search API:             http://localhost:8015"
    echo "🌐 Kong Gateway:           http://localhost:8100"
    echo "🔧 Kong Admin:             http://localhost:8102"
    echo "🗄️  PostgreSQL:             localhost:5433"
    echo "🔴 Redis:                  localhost:6380"
    echo "📊 Elasticsearch:          http://localhost:9201"
    echo "📨 Kafka:                  localhost:9095"
    echo
    echo "📖 API Documentation:"
    echo "--------------------"
    echo "🔐 Auth API:               http://localhost:8010/docs"
    echo "📄 Document API:           http://localhost:8011/docs"
    echo "⚙️  Processing API:         http://localhost:8013/docs"
    echo "🔍 Search Indexing API:    http://localhost:8014/docs"
    echo "🔎 Search API:             http://localhost:8015/docs"
    echo
    echo "🧪 Testing the Setup:"
    echo "--------------------"
    echo "1. Test auth service:      curl http://localhost:8010/health"
    echo "2. Test document service:  curl http://localhost:8011/health"
    echo "3. Test processing service: curl http://localhost:8013/health"
    echo "4. Test search indexing:   curl http://localhost:8014/health"
    echo "5. Test search API:        curl http://localhost:8015/health"
    echo
    echo "📚 Next Steps:"
    echo "-------------"
    echo "1. Register a user:        POST http://localhost:8010/api/v1/auth/register"
    echo "2. Login to get token:     POST http://localhost:8010/api/v1/auth/login"
    echo "3. Upload a document:      POST http://localhost:8011/api/v1/documents/upload"
    echo "4. Check processing:       Monitor processing logs"
    echo "5. Search documents:       POST http://localhost:8015/api/v1/search/"
    echo "6. Monitor logs:           docker-compose -f docker-compose.dev.yml logs -f"
    echo
    echo "🛠️  Useful Commands:"
    echo "------------------"
    echo "• View logs:               docker-compose -f docker-compose.dev.yml logs -f [service-name]"
    echo "• Stop all services:       docker-compose -f docker-compose.dev.yml down"
    echo "• Restart a service:       docker-compose -f docker-compose.dev.yml restart [service-name]"
    echo "• View service status:     docker-compose -f docker-compose.dev.yml ps"
    echo
}

# Main execution
main() {
    print_status "Starting Medical AI Platform development setup..."
    
    # Pre-flight checks
    check_docker
    check_docker_compose
    check_ports
    
    # Setup
    setup_env_files
    setup_permissions
    
    # Start services
    start_infrastructure
    start_applications
    
    # Show results
    show_service_info
    
    print_success "Setup complete! Your Medical AI Platform development environment is ready."
}

# Handle script interruption
trap 'print_error "Setup interrupted. You may need to clean up with: docker-compose -f docker-compose.dev.yml down"' INT

# Run main function
main "$@"