#!/bin/bash

# Complete rebuild script for Social Media Publisher System
# Usage: ./rebuild_social_media_system.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_blue() {
    echo -e "${BLUE}[BUILD]${NC} $1"
}

log_purple() {
    echo -e "${PURPLE}[SYSTEM]${NC} $1"
}

# Check if docker-compose.yaml exists
if [ ! -f "docker-compose.yaml" ]; then
    log_error "❌ docker-compose.yaml not found in current directory!"
    log_info "Please run this script from the root directory containing docker-compose.yaml"
    exit 1
fi

log_info "🚀 Starting complete rebuild of Social Media Publisher System..."
log_purple "🏗️ System: Multi-Sites Social Media Automation Platform"

# Services defined in docker-compose.yaml
SERVICES=(
    "social-media-api:8090"
    "social-media-worker-content:N/A"
    "social-media-worker-publishing:N/A"
    "social-media-beat:N/A"
    "social-media-flower:5555"
    "social-media-redis:6379"
    "social-media-db:5432"
)

echo ""
log_info "📋 Services to rebuild:"
for service in "${SERVICES[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if [ "$port" = "N/A" ]; then
        echo "  🔧 $name (background worker/scheduler)"
    elif [ "$port" = "6379" ]; then
        echo "  🗄️ $name (Redis cache/queue)"
    elif [ "$port" = "5432" ]; then
        echo "  🗃️ $name (PostgreSQL database)"
    else
        echo "  🌐 $name (HTTP service - port $port)"
    fi
done
echo ""

log_info "🛑 Stopping all Social Media Publisher services..."
docker compose down

# Force stop all containers that might be using our networks/ports
log_info "🧹 Force stopping all related containers..."
docker ps -a --format "table {{.Names}}" | grep -E "(social-media|social_media)" | xargs -r docker stop 2>/dev/null || true
docker ps -a --format "table {{.Names}}" | grep -E "(social-media|social_media)" | xargs -r docker rm 2>/dev/null || true

# Remove containers by pattern
docker rm -f $(docker ps -aq --filter "name=social-media") 2>/dev/null || true
docker rm -f $(docker ps -aq --filter "name=social_media") 2>/dev/null || true

# Check for containers still using networks and force remove them
log_info "🔍 Checking for containers using our networks..."
for network in "social-media-network" "social_media_default" "social-media_default"; do
    if docker network inspect $network >/dev/null 2>&1; then
        log_info "Disconnecting all containers from network: $network"
        # Get container IDs connected to this network
        CONTAINER_IDS=$(docker network inspect $network --format '{{range $id, $v := .Containers}}{{printf "%s " $id}}{{end}}' 2>/dev/null || true)
        if [ ! -z "$CONTAINER_IDS" ]; then
            for container_id in $CONTAINER_IDS; do
                docker network disconnect -f $network $container_id 2>/dev/null || true
            done
        fi
    fi
done

# Additional cleanup for port conflicts
log_info "🔍 Checking for port conflicts..."
for port in 8090 5555 6379 5432; do
  CONTAINER_ID=$(docker ps -q --filter publish=$port)
  if [ ! -z "$CONTAINER_ID" ]; then
    log_warn "Found container using port $port: $CONTAINER_ID"
    log_info "Stopping and removing container..."
    docker stop $CONTAINER_ID 2>/dev/null || true
    docker rm $CONTAINER_ID 2>/dev/null || true
  fi
done

# Remove all networks
log_info "🌐 Removing all related networks..."
docker network rm social-media-network social_media_default social-media_default 2>/dev/null || true

# Remove all images
log_info "🗑️ Removing existing images..."
docker compose down --rmi all 2>/dev/null || true

# Additional cleanup for any remaining images
docker rmi social-media-social-media-api social-media-social-media-worker-content social-media-social-media-worker-publishing social-media-social-media-beat social-media-social-media-flower 2>/dev/null || true

# Clean up dangling images and volumes
log_info "🧹 Cleaning up dangling resources..."
docker image prune -f
docker volume prune -f
docker network prune -f

# Clean build cache
log_info "🧹 Cleaning Docker build cache..."
docker builder prune -f

# Build all services
log_blue "🔨 Building all Social Media Publisher services..."
docker compose build --no-cache --parallel

# Start infrastructure services first (Redis and PostgreSQL)
log_info "🚀 Starting infrastructure services..."
docker compose up -d social-media-redis social-media-db

# Wait for infrastructure to be ready
log_info "⏳ Waiting for infrastructure services to be ready..."
sleep 15

# Check Redis connectivity
log_info "🔍 Checking Redis connectivity..."
for i in {1..12}; do
    if docker exec social-media-social-media-redis-1 redis-cli ping >/dev/null 2>&1; then
        log_info "✅ Redis is ready"
        break
    else
        log_warn "⚠️ Redis not ready, attempt $i/12..."
        sleep 5
    fi
done

# Check PostgreSQL connectivity
log_info "🔍 Checking PostgreSQL connectivity..."
for i in {1..12}; do
    if docker exec social-media-social-media-db-1 pg_isready -U ${POSTGRES_USER:-social_media_user} >/dev/null 2>&1; then
        log_info "✅ PostgreSQL is ready"
        break
    else
        log_warn "⚠️ PostgreSQL not ready, attempt $i/12..."
        sleep 5
    fi
done

# Start Celery workers
log_info "🚀 Starting Celery workers..."
docker compose up -d social-media-worker-content social-media-worker-publishing

# Wait for workers to start
log_info "⏳ Waiting for workers to start..."
sleep 10

# Start scheduler
log_info "🚀 Starting Celery Beat scheduler..."
docker compose up -d social-media-beat

# Wait for scheduler
log_info "⏳ Waiting for scheduler..."
sleep 5

# Start main API service
log_info "🚀 Starting main API service..."
docker compose up -d social-media-api

# Wait for API to be ready
log_info "⏳ Waiting for API service to be ready..."
sleep 20

# Start monitoring (Flower)
log_info "🚀 Starting monitoring service..."
docker compose up -d social-media-flower

# Wait for all services to be ready
log_info "⏳ Final startup wait..."
sleep 15

# Function to check service health
check_service_health() {
    local service_name=$1
    local port=$2
    local max_attempts=12
    local attempt=1

    if [ "$port" = "N/A" ]; then
        log_info "⚠️ $service_name is a worker/background service (no health check)"
        return 0
    fi

    if [ "$port" = "6379" ] || [ "$port" = "5432" ]; then
        log_info "⚠️ $service_name is a database service (checked separately)"
        return 0
    fi

    log_info "🏥 Checking $service_name health on port $port..."

    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:$port/health &> /dev/null; then
            log_info "✅ $service_name is healthy"
            return 0
        else
            log_warn "⚠️ $service_name not ready, attempt $attempt/$max_attempts..."
            sleep 5
            ((attempt++))
        fi
    done

    log_error "❌ $service_name failed to start properly"
    return 1
}

# Check health of all services
services_status=()
all_healthy=true

# Check HTTP services
for service_info in "${SERVICES[@]}"; do
    IFS=':' read -r service_name port <<< "$service_info"

    if [ "$port" = "8090" ] || [ "$port" = "5555" ]; then
        if check_service_health "$service_name" "$port"; then
            services_status+=("$service_name:OK")
        else
            services_status+=("$service_name:FAIL")
            all_healthy=false
        fi
    else
        services_status+=("$service_name:WORKER")
    fi
done

# Check Redis connectivity (already done above, but verify again)
log_info "🔍 Final Redis connectivity check..."
if docker exec social-media-social-media-redis-1 redis-cli ping >/dev/null 2>&1; then
    services_status+=("social-media-redis:OK")
    log_info "✅ Redis is healthy"
else
    services_status+=("social-media-redis:FAIL")
    log_error "❌ Redis is unhealthy"
    all_healthy=false
fi

# Check PostgreSQL connectivity
log_info "🔍 Final PostgreSQL connectivity check..."
if docker exec social-media-social-media-db-1 pg_isready -U ${POSTGRES_USER:-social_media_user} >/dev/null 2>&1; then
    services_status+=("social-media-db:OK")
    log_info "✅ PostgreSQL is healthy"
else
    services_status+=("social-media-db:FAIL")
    log_error "❌ PostgreSQL is unhealthy"
    all_healthy=false
fi

# Show results
echo ""
log_info "📋 Container status:"
docker compose ps

echo ""
log_purple "🌐 Social Media Publisher Service Endpoints:"
echo "  📍 Main API: http://localhost:8090"
echo "  📍 API Health: http://localhost:8090/health"
echo "  📍 API Docs: http://localhost:8090/docs"
echo "  📍 Celery Monitoring (Flower): http://localhost:5555"
echo "  📍 Account Management: http://localhost:8090/accounts"
echo "  📍 Credentials Status: http://localhost:8090/credentials"

echo ""
log_purple "🔗 Multi-Site Publishing Endpoints:"
echo "  📝 Simple Publishing: POST http://localhost:8090/publish"
echo "  🚀 Advanced Publishing: POST http://localhost:8090/publish/advanced"
echo "  📊 Publication Status: GET http://localhost:8090/status/{request_id}"
echo "  🧪 Test Formatting: POST http://localhost:8090/test/format/advanced"
echo "  ✅ Test Credentials: POST http://localhost:8090/test/credentials"

echo ""
log_purple "⚙️ Queue Systems & Workers:"
echo "  📊 Content Generation Queue: content_generation"
echo "  📊 Content Formatting Queue: content_formatting"
echo "  📊 Content Publishing Queue: content_publishing"
echo "  📊 Image Generation Queue: image_generation"
echo "  🔄 Redis Connection: redis://social-media-redis:6379/1"
echo "  🗃️ PostgreSQL: social-media-db:5432"

echo ""
log_purple "🏢 Multi-Site Support:"
echo "  🎮 StuffGaming.fr (Instagram, Twitter, Facebook)"
echo "  🎯 Gaming.com (Instagram, Twitter, Facebook)"
echo "  ⚽ Football.com (Instagram, Twitter, Facebook)"
echo "  📊 Total: 9 social media accounts"

echo ""
log_info "🌐 Network information:"
docker network ls | grep social-media || log_warn "social-media-network not found"

# Show service status summary
echo ""
log_info "📊 Service status summary:"
for status in "${services_status[@]}"; do
    IFS=':' read -r service result <<< "$status"
    if [[ $result == "OK" ]]; then
        log_info "  ✅ $service: HEALTHY"
    elif [[ $result == "WORKER" ]]; then
        log_info "  ⚙️ $service: WORKER SERVICE"
    else
        log_error "  ❌ $service: UNHEALTHY"
    fi
done

echo ""
if [ "$all_healthy" = true ]; then
    log_info "🎉 Social Media Publisher System is fully operational!"
    echo ""
    log_purple "💡 Quick Start Examples:"
    echo ""
    echo "  📝 Simple multi-platform publication:"
    echo '  curl -X POST "http://localhost:8090/publish" \'
    echo '    -H "Content-Type: application/json" \'
    echo '    -d "{\"texte_source\": \"Hello from our new AI system!\", \"site_web\": \"stuffgaming.fr\", \"plateformes\": [\"twitter\", \"instagram\", \"facebook\"], \"hashtags\": [\"#AI\", \"#Gaming\"]}"'
    echo ""
    echo "  🎯 Instagram carousel with images:"
    echo '  curl -X POST "http://localhost:8090/publish/advanced" \'
    echo '    -H "Content-Type: application/json" \'
    echo '    -d "{\"texte_source\": \"Top 5 games 2024\", \"site_web\": \"stuffgaming.fr\", \"platforms_config\": [{\"platform\": \"instagram\", \"content_type\": \"carousel\", \"nb_slides\": 5, \"hashtags\": [\"#gaming\", \"#top5\"]}]}"'
    echo ""
    echo "  📊 Check all accounts:"
    echo "  curl http://localhost:8090/accounts"
    echo ""
    echo "  🔐 Validate credentials:"
    echo '  curl -X POST "http://localhost:8090/test/credentials" -d "site_web=stuffgaming.fr&platform=twitter"'
    echo ""
    log_info "🔧 Useful management commands:"
    echo "  📋 View logs: docker compose logs [service-name]"
    echo "  📊 View worker logs: docker compose logs social-media-worker-content"
    echo "  🛑 Stop all: docker compose down"
    echo "  🔄 Restart: docker compose restart [service-name]"
    echo "  📈 Monitor queues: docker compose exec social-media-redis redis-cli monitor"
    echo "  🌸 View Celery tasks: http://localhost:5555"
else
    log_error "⚠️ Some services are not healthy. Check the logs."
    echo ""
    log_info "🔍 To check logs:"
    echo "  docker compose logs social-media-api"
    echo "  docker compose logs social-media-worker-content"
    echo "  docker compose logs social-media-worker-publishing"
    echo "  docker compose logs social-media-redis"
    echo "  docker compose logs social-media-db"
    echo ""
    log_info "🔧 To restart a specific service:"
    echo "  docker compose restart [service-name]"
fi

echo ""
log_info "🏁 Social Media Publisher System rebuild complete!"

# Optional: Show environment check
echo ""
log_info "🔍 Environment configuration check:"
if [ -f ".env" ]; then
    log_info "  ✅ .env file found"
else
    log_warn "  ⚠️ .env file not found - make sure environment variables are set"
    log_info "  💡 Copy .env.example to .env and configure your credentials"
fi

# Check if required environment variables are mentioned in docker-compose
required_vars=("ANTHROPIC_API_KEY" "STUFFGAMING_FR_TWITTER_API_KEY" "GAMING_COM_FACEBOOK_ACCESS_TOKEN" "FOOTBALL_COM_INSTAGRAM_ACCESS_TOKEN")
missing_vars=()

for var in "${required_vars[@]}"; do
    if ! grep -q "$var" docker-compose.yaml; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -eq 0 ]; then
    log_info "  ✅ Key environment variables are referenced in docker-compose.yaml"
else
    log_warn "  ⚠️ Some environment variables might be missing from docker-compose.yaml:"
    for var in "${missing_vars[@]}"; do
        echo "    - $var"
    done
fi

echo ""
log_purple "🎯 Queue System Status:"
echo "  📊 Check content generation queue: docker compose exec social-media-redis redis-cli llen content_generation"
echo "  📊 Check publishing queue: docker compose exec social-media-redis redis-cli llen content_publishing"
echo "  📊 Monitor all workers: docker compose logs -f social-media-worker-content social-media-worker-publishing"
echo "  🌸 Celery monitoring UI: http://localhost:5555"

echo ""
log_purple "🏢 Multi-Site Credentials Check:"
echo "  🔐 StuffGaming credentials: curl http://localhost:8090/credentials/stuffgaming.fr/twitter"
echo "  🔐 Gaming credentials: curl http://localhost:8090/credentials/gaming.com/facebook"
echo "  🔐 Football credentials: curl http://localhost:8090/credentials/football.com/instagram"
echo "  📊 All credentials status: curl http://localhost:8090/credentials"

echo ""
log_info "🚀 System ready for multi-site social media automation!"