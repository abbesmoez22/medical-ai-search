#!/bin/bash
set -e

# Function to create database if it doesn't exist
create_database() {
    local database=$1
    echo "Creating database '$database'"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        SELECT 'CREATE DATABASE $database'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
EOSQL
}

# Create databases for each service
create_database "auth_db"
create_database "document_db"  
create_database "processing_db"
create_database "search_db"

echo "All databases created successfully!"

# Grant permissions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    GRANT ALL PRIVILEGES ON DATABASE auth_db TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE document_db TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE processing_db TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON DATABASE search_db TO $POSTGRES_USER;
EOSQL

echo "Database permissions granted successfully!"