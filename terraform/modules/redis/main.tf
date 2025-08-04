# ElastiCache Redis Module for Medical AI Search Platform
# Redis cluster with encryption and monitoring

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Subnet Group for ElastiCache
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-redis-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-redis-subnet-group"
    Type = "elasticache-subnet-group"
  })
}

# Security Group for Redis
resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-${var.environment}-redis-"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = var.allowed_security_groups
    description     = "Redis access from EKS"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-redis-sg"
    Type = "security-group"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Parameter Group for Redis optimization
resource "aws_elasticache_parameter_group" "main" {
  family = "redis7"
  name   = "${var.project_name}-${var.environment}-redis-params"

  # Memory optimization
  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  # Connection timeout
  parameter {
    name  = "timeout"
    value = "300"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-redis-params"
    Type = "elasticache-parameter-group"
  })
}

# Redis Replication Group (Cluster)
resource "aws_elasticache_replication_group" "main" {
  replication_group_id         = "${var.project_name}-${var.environment}-redis"
  description                  = "Redis cluster for ${var.project_name} ${var.environment}"
  
  # Node configuration
  node_type               = var.node_type
  port                    = 6379
  parameter_group_name    = aws_elasticache_parameter_group.main.name
  
  # Cluster configuration
  num_cache_clusters      = var.num_cache_clusters
  
  # Network configuration
  subnet_group_name       = aws_elasticache_subnet_group.main.name
  security_group_ids      = [aws_security_group.redis.id]
  
  # Encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.auth_token
  
  # Backup configuration
  automatic_failover_enabled = var.num_cache_clusters > 1
  multi_az_enabled          = var.num_cache_clusters > 1
  snapshot_retention_limit  = var.snapshot_retention_limit
  snapshot_window          = var.snapshot_window
  
  # Maintenance
  maintenance_window       = var.maintenance_window
  auto_minor_version_upgrade = true
  
  # Logging
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow.name
    destination_type = "cloudwatch-logs"
    log_format       = "text"
    log_type         = "slow-log"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-redis-cluster"
    Type = "elasticache-replication-group"
  })

  depends_on = [
    aws_elasticache_subnet_group.main,
    aws_elasticache_parameter_group.main
  ]
}

# CloudWatch Log Groups for Redis logs
resource "aws_cloudwatch_log_group" "redis_slow" {
  name              = "/aws/elasticache/${var.project_name}-${var.environment}-redis/slow-log"
  retention_in_days = var.log_retention_days

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-redis-slow-log"
    Type = "log-group"
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${var.project_name}-${var.environment}-redis-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors Redis CPU utilization"
  alarm_actions       = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.main.replication_group_id}-001"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-redis-cpu-alarm"
    Type = "cloudwatch-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  alarm_name          = "${var.project_name}-${var.environment}-redis-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors Redis memory utilization"
  alarm_actions       = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.main.replication_group_id}-001"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-redis-memory-alarm"
    Type = "cloudwatch-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "redis_connections" {
  alarm_name          = "${var.project_name}-${var.environment}-redis-current-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CurrConnections"
  namespace           = "AWS/ElastiCache"
  period              = "120"
  statistic           = "Average"
  threshold           = "1000"
  alarm_description   = "This metric monitors Redis current connections"
  alarm_actions       = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.main.replication_group_id}-001"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-redis-connections-alarm"
    Type = "cloudwatch-alarm"
  })
}

resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  alarm_name          = "${var.project_name}-${var.environment}-redis-evictions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors Redis evictions"
  alarm_actions       = var.sns_topic_arn != null ? [var.sns_topic_arn] : []

  dimensions = {
    CacheClusterId = "${aws_elasticache_replication_group.main.replication_group_id}-001"
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-redis-evictions-alarm"
    Type = "cloudwatch-alarm"
  })
} 