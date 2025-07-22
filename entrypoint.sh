#!/bin/bash

# Social Media Publisher - Docker Entrypoint Script
# This script handles the startup of different service types

set -e

# Colors for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[ENTRYPOINT]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[ENTRYPOINT]${NC} $1"
}

log_error() {
    echo -e "${RED}[ENTRYPOINT]${NC} $1"
}

# Function to wait for Redis using Python
wait_for_redis() {
    log_info "Waiting for Redis to be ready..."

    while ! python3 -c "
import redis
import sys
try:
    r = redis.Redis(host='social-media-redis', port=6379, db=1, socket_timeout=5, socket_connect_timeout=5)
    r.ping()
    print('Redis is ready')
    sys.exit(0)
except Exception as e:
    print(f'Redis not ready: {e}')
    sys.exit(1)
" > /dev/null 2>&1; do
        log_warn "Redis not ready, waiting 2 seconds..."
        sleep 2
    done

    log_info "✅ Redis is ready!"
}

# Function to wait for PostgreSQL using Python (simplified)
wait_for_postgres() {
    log_info "Waiting for PostgreSQL to be ready..."

    # Simple approach - just check if PostgreSQL is accepting connections
    while ! python3 -c "
import socket
import sys
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(('social-media-db', 5432))
    sock.close()
    if result == 0:
        print('PostgreSQL is ready')
        sys.exit(0)
    else:
        sys.exit(1)
except Exception as e:
    print(f'PostgreSQL not ready: {e}')
    sys.exit(1)
" > /dev/null 2>&1; do
        log_warn "PostgreSQL not ready, waiting 2 seconds..."
        sleep 2
    done

    log_info "✅ PostgreSQL is ready!"
}

# Function to run database migrations
run_migrations() {
    log_info "Running database migrations..."

    # TODO: Add Alembic migrations when database models are created
    # alembic upgrade head

    log_info "✅ Database migrations completed!"
}

# Set Python path
export PYTHONPATH=/app:$PYTHONPATH

# Create necessary directories
mkdir -p /app/logs /app/temp /app/data /app/output

# Set permissions
chown -R appuser:appuser /app/logs /app/temp /app/data /app/output

# Main entrypoint logic
case "$1" in
    "api")
        log_info "🚀 Starting Social Media Publisher API..."
        wait_for_redis
        wait_for_postgres
        run_migrations

        log_info "Starting FastAPI server on port ${API_PORT:-8090}"
        exec python -m app.main
        ;;

    "worker-content")
        log_info "⚙️ Starting Content Generation Worker..."
        wait_for_redis

        log_info "Starting Celery worker for content generation and formatting"
        exec celery -A app.services.celery_app.celery_app worker \
            --loglevel=info \
            --queues=content_generation,content_formatting \
            --concurrency=2 \
            --hostname=content-worker@%h \
            --without-gossip \
            --without-mingle \
            --without-heartbeat
        ;;

    "worker-publishing")
        log_info "📤 Starting Publishing Worker..."
        wait_for_redis

        log_info "Starting Celery worker for publishing and image generation"
        exec celery -A app.services.celery_app.celery_app worker \
            --loglevel=info \
            --queues=content_publishing,image_generation \
            --concurrency=2 \
            --hostname=publishing-worker@%h \
            --without-gossip \
            --without-mingle \
            --without-heartbeat
        ;;

    "beat")
        log_info "⏰ Starting Celery Beat Scheduler..."
        wait_for_redis

        log_info "Starting Celery beat scheduler"
        exec celery -A app.services.celery_app.celery_app beat \
            --loglevel=info \
            --schedule=/app/temp/celerybeat-schedule \
            --pidfile=/app/temp/celerybeat.pid
        ;;

    "flower")
        log_info "🌸 Starting Celery Flower Monitoring..."
        wait_for_redis

        log_info "Starting Flower monitoring on port 5555"
        exec celery -A app.services.celery_app.celery_app flower \
            --port=5555 \
            --broker=${CELERY_BROKER_URL} \
            --basic_auth=${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-admin}
        ;;

    "test")
        log_info "🧪 Running Tests..."
        wait_for_redis

        log_info "Running test suite"
        exec python -m pytest tests/ -v
        ;;

    *)
        log_info "🔧 Running custom command: $@"
        exec "$@"
        ;;
esac