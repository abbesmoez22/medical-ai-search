# Medical AI Search Platform - Backend Services

## Overview

This is the **Phase 2: Core Backend Services** implementation for the enterprise-grade medical AI search platform. The backend is built using modern microservices architecture with event-driven patterns, showcasing distributed systems expertise and FAANG-level engineering practices.

## Architecture

### Microservices Design
- **Event-Driven Architecture**: Kafka-based communication between services
- **API Gateway Pattern**: Kong for request routing and rate limiting  
- **Database per Service**: Each microservice owns its data
- **CQRS Pattern**: Command Query Responsibility Segregation where applicable
- **Circuit Breaker Pattern**: Resilience and fault tolerance

### Technology Stack
- **Language**: Python 3.11+ with FastAPI
- **Message Queue**: Apache Kafka with Confluent Platform
- **API Gateway**: Kong Gateway with plugins
- **Databases**: PostgreSQL, Redis
- **Search**: Elasticsearch
- **Authentication**: JWT with OAuth2 flows
- **Documentation**: OpenAPI/Swagger with automatic generation

## Services

### 1. Authentication Service ✅
**Status**: Implemented  
**Port**: 8001  
**Purpose**: Handle user registration, authentication, and authorization

**Features:**
- User registration and email verification
- JWT token generation and validation
- Role-based access control (RBAC)
- Session management with Redis
- Password reset workflows
- Audit logging for security events
- Rate limiting on authentication endpoints

**Endpoints:**
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Token refresh
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/change-password` - Change password
- `POST /api/v1/auth/forgot-password` - Request password reset
- `POST /api/v1/auth/reset-password` - Reset password
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update user profile

### 2. Document Management Service 🚧
**Status**: Pending  
**Port**: 8002  
**Purpose**: Handle medical document upload, processing, and metadata management

### 3. Content Processing Service 🚧
**Status**: Pending  
**Port**: 8003  
**Purpose**: Extract and process content from medical documents

### 4. Search Indexing Service 🚧
**Status**: Pending  
**Port**: 8004  
**Purpose**: Index processed documents for full-text and semantic search

### 5. Search API Service 🚧
**Status**: Pending  
**Port**: 8005  
**Purpose**: Provide unified search interface with multiple search strategies

### 6. Notification Service 🚧
**Status**: Pending  
**Port**: 8006  
**Purpose**: Handle all system notifications and communications

## Infrastructure Services

### PostgreSQL
- **Port**: 5432
- **Credentials**: postgres/password
- **Databases**: auth_db, document_db, processing_db, search_db

### Redis
- **Port**: 6379
- **Purpose**: Caching, session management, rate limiting

### Apache Kafka
- **Port**: 9092 (internal), 9094 (external)
- **Purpose**: Event-driven communication between services

### Elasticsearch
- **Port**: 9200
- **Purpose**: Full-text search and document indexing

### Kong Gateway
- **Port**: 8000 (proxy), 8001 (admin)
- **Purpose**: API gateway, authentication, rate limiting

## Quick Start

### Prerequisites
- Docker and Docker Compose
- At least 8GB RAM available for containers
- Ports 5432, 6379, 8000-8006, 9092, 9200 available

### Development Setup

1. **Clone and navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Run the setup script:**
   ```bash
   ./scripts/setup-dev.sh
   ```

3. **Verify services are running:**
   ```bash
   docker-compose -f docker-compose.dev.yml ps
   ```

4. **Check service health:**
   ```bash
   curl http://localhost:8001/health  # Auth service
   ```

### Manual Setup

If you prefer manual setup:

1. **Start infrastructure services:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d postgres redis zookeeper kafka elasticsearch
   ```

2. **Wait for services to be ready (30-60 seconds):**
   ```bash
   docker-compose -f docker-compose.dev.yml logs -f kafka
   ```

3. **Start application services:**
   ```bash
   docker-compose -f docker-compose.dev.yml up -d --build auth-service
   ```

## Development Workflow

### Running Services
```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Start specific service
docker-compose -f docker-compose.dev.yml up -d auth-service

# View logs
docker-compose -f docker-compose.dev.yml logs -f auth-service

# Stop all services
docker-compose -f docker-compose.dev.yml down
```

### Testing
```bash
# Run tests for auth service
docker-compose -f docker-compose.dev.yml exec auth-service pytest

# Run tests with coverage
docker-compose -f docker-compose.dev.yml exec auth-service pytest --cov=app
```

### Database Operations
```bash
# Connect to PostgreSQL
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d auth_db

# Connect to Redis
docker-compose -f docker-compose.dev.yml exec redis redis-cli
```

### Code Quality
```bash
# Format code
docker-compose -f docker-compose.dev.yml exec auth-service black app/

# Sort imports
docker-compose -f docker-compose.dev.yml exec auth-service isort app/

# Lint code
docker-compose -f docker-compose.dev.yml exec auth-service flake8 app/

# Type checking
docker-compose -f docker-compose.dev.yml exec auth-service mypy app/
```

## API Documentation

### Authentication Service
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **OpenAPI JSON**: http://localhost:8001/openapi.json

### Example API Usage

1. **Register a new user:**
   ```bash
   curl -X POST "http://localhost:8001/api/v1/auth/register" \
        -H "Content-Type: application/json" \
        -d '{
          "email": "doctor@example.com",
          "username": "drsmith",
          "password": "SecurePass123!",
          "first_name": "John",
          "last_name": "Smith",
          "role": "doctor",
          "specialty": "cardiology",
          "institution": "City Hospital"
        }'
   ```

2. **Login:**
   ```bash
   curl -X POST "http://localhost:8001/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
          "email": "doctor@example.com",
          "password": "SecurePass123!"
        }'
   ```

3. **Get user profile:**
   ```bash
   curl -X GET "http://localhost:8001/api/v1/users/me" \
        -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

## Event-Driven Architecture

### Kafka Topics
- `medical-ai-platform.user.events` - User lifecycle events
- `medical-ai-platform.document.events` - Document processing events
- `medical-ai-platform.search.events` - Search analytics events
- `medical-ai-platform.notification.events` - Notification requests
- `medical-ai-platform.system.events` - System-wide events

### Event Types
- `user.registered` - New user registration
- `user.login` - User login attempt
- `user.logout` - User logout
- `document.uploaded` - New document uploaded
- `document.processed` - Document processing completed
- `search.performed` - Search query executed

## Monitoring & Observability

### Health Checks
- Auth Service: http://localhost:8001/health
- PostgreSQL: `docker-compose exec postgres pg_isready`
- Redis: `docker-compose exec redis redis-cli ping`
- Kafka: `docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092`

### Logs
```bash
# View all service logs
docker-compose -f docker-compose.dev.yml logs -f

# View specific service logs
docker-compose -f docker-compose.dev.yml logs -f auth-service

# View infrastructure logs
docker-compose -f docker-compose.dev.yml logs -f postgres redis kafka
```

### Metrics
- Application metrics are logged in structured JSON format
- Health check endpoints provide service status
- Database connection pooling metrics available
- Kafka producer/consumer metrics logged

## Security

### Authentication & Authorization
- JWT tokens with short expiration (30 minutes)
- Refresh token rotation for security
- Role-based access control (RBAC)
- Account lockout after failed attempts
- Rate limiting on authentication endpoints

### Data Protection
- Password hashing with bcrypt
- Sensitive data encrypted in transit
- Input validation and sanitization
- SQL injection prevention with SQLAlchemy
- CORS configuration for web security

## Troubleshooting

### Common Issues

1. **Services not starting:**
   ```bash
   # Check Docker resources
   docker system df
   docker system prune
   
   # Restart services
   docker-compose -f docker-compose.dev.yml restart
   ```

2. **Database connection errors:**
   ```bash
   # Check PostgreSQL logs
   docker-compose -f docker-compose.dev.yml logs postgres
   
   # Restart PostgreSQL
   docker-compose -f docker-compose.dev.yml restart postgres
   ```

3. **Kafka connection issues:**
   ```bash
   # Check Kafka logs
   docker-compose -f docker-compose.dev.yml logs kafka
   
   # Verify Kafka topics
   docker-compose -f docker-compose.dev.yml exec kafka kafka-topics --list --bootstrap-server localhost:9092
   ```

### Port Conflicts
If you have port conflicts, modify the ports in `docker-compose.dev.yml`:
```yaml
services:
  postgres:
    ports:
      - "5433:5432"  # Change external port
```

## Production Considerations

### Environment Variables
- Use strong, unique `SECRET_KEY` values
- Configure proper database credentials
- Set up email SMTP settings for notifications
- Configure OAuth providers for social login

### Scaling
- Each service can be scaled independently
- Database connection pooling configured
- Kafka partitioning for horizontal scaling
- Redis clustering for high availability

### Security Hardening
- Use environment-specific secrets
- Enable TLS for all communications
- Configure proper CORS origins
- Set up proper logging and monitoring
- Regular security updates

## Next Steps

1. **Document Management Service** - File upload and metadata management
2. **Content Processing Service** - PDF extraction and medical NER
3. **Search Services** - Elasticsearch integration and search APIs
4. **API Gateway Configuration** - Kong setup with authentication
5. **Monitoring Setup** - Prometheus, Grafana, and alerting
6. **CI/CD Pipeline** - Automated testing and deployment

## Contributing

1. Follow the existing code structure and patterns
2. Add comprehensive tests for new features
3. Update documentation for any API changes
4. Use structured logging for all operations
5. Follow the event-driven architecture patterns

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review service logs for error details
3. Verify all prerequisites are met
4. Check Docker resource availability