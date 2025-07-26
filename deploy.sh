#!/bin/bash
# deploy.sh - Social Media Publisher with Intelligent Cropping Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="social-media-publisher"
DOCKER_COMPOSE_FILE="docker-compose.yaml"

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

# Function to check if .env file exists
check_env_file() {
    if [ ! -f ".env" ]; then
        print_error ".env file not found!"
        print_status "Creating .env from .env.example..."

        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_warning "Please edit .env file with your actual credentials before proceeding"
            print_status "Required variables:"
            echo "  - ANTHROPIC_API_KEY"
            echo "  - AWS_ACCESS_KEY_ID"
            echo "  - AWS_SECRET_ACCESS_KEY"
            echo "  - Social media credentials (Twitter, Facebook, Instagram)"
            read -p "Press Enter when you've updated the .env file..."
        else
            print_error ".env.example not found. Please create .env manually."
            exit 1
        fi
    else
        print_success ".env file found"
    fi
}

# Function to check system requirements
check_requirements() {
    print_status "Checking system requirements..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi

    # Check available disk space (need at least 5GB for SAM models)
    available_space=$(df . | tail -1 | awk '{print $4}')
    required_space=5242880  # 5GB in KB

    if [ "$available_space" -lt "$required_space" ]; then
        print_warning "Low disk space detected. SAM models require ~2GB+ of storage."
        print_status "Available: $(($available_space / 1024))MB, Recommended: 5GB+"
    fi

    print_success "System requirements check passed"
}

# Function to setup SAM checkpoints
setup_sam_checkpoints() {
    print_status "Setting up SAM (Segment Anything Model) checkpoints..."

    # Create checkpoints directory
    mkdir -p ./sam_checkpoints

    # Check if SAM is enabled in .env
    if grep -q "SAM_ENABLED=true" .env 2>/dev/null; then
        print_status "SAM is enabled. Checkpoints will be downloaded automatically on first run."

        # Ask user which model to use
        echo "SAM Model Options:"
        echo "  1) vit_b (358MB, fast, good quality) - Recommended"
        echo "  2) vit_l (1.2GB, slower, better quality)"
        echo "  3) vit_h (2.4GB, slowest, best quality)"
        read -p "Choose SAM model [1-3, default: 1]: " sam_choice

        case $sam_choice in
            2)
                sed -i 's/SAM_MODEL_TYPE=.*/SAM_MODEL_TYPE=vit_l/' .env 2>/dev/null || true
                print_status "Selected SAM ViT-L model"
                ;;
            3)
                sed -i 's/SAM_MODEL_TYPE=.*/SAM_MODEL_TYPE=vit_h/' .env 2>/dev/null || true
                print_status "Selected SAM ViT-H model"
                ;;
            *)
                sed -i 's/SAM_MODEL_TYPE=.*/SAM_MODEL_TYPE=vit_b/' .env 2>/dev/null || true
                print_status "Selected SAM ViT-B model (default)"
                ;;
        esac
    else
        print_warning "SAM is disabled. Only OpenCV-based cropping will be available."
    fi
}

# Function to build and start services
start_services() {
    print_status "Building and starting services..."

    # Build images
    print_status "Building Docker images..."
    docker-compose -f $DOCKER_COMPOSE_FILE build

    # Start infrastructure services first
    print_status "Starting infrastructure services (Redis, PostgreSQL)..."
    docker-compose -f $DOCKER_COMPOSE_FILE up -d social-media-redis social-media-db

    # Wait for infrastructure to be ready
    print_status "Waiting for infrastructure to be ready..."
    sleep 10

    # Start main application
    print_status "Starting main application..."
    docker-compose -f $DOCKER_COMPOSE_FILE up -d social-media-api

    # Start workers
    print_status "Starting Celery workers..."
    docker-compose -f $DOCKER_COMPOSE_FILE up -d \
        social-media-worker-content \
        social-media-worker-formatting \
        social-media-worker-image \
        social-media-worker-publishing

    # Start scheduler and monitoring
    print_status "Starting scheduler and monitoring..."
    docker-compose -f $DOCKER_COMPOSE_FILE up -d \
        social-media-beat \
        social-media-flower

    print_success "All services started successfully!"
}

# Function to test the deployment
test_deployment() {
    print_status "Testing deployment..."

    # Wait for API to be ready
    print_status "Waiting for API to be ready..."
    sleep 30

    # Test API health
    if curl -f http://localhost:8090/health &> /dev/null; then
        print_success "API is responding"
    else
        print_error "API is not responding"
        return 1
    fi

    # Test crop system status
    if curl -f http://localhost:8090/crop/status &> /dev/null; then
        print_success "Intelligent crop system is available"
    else
        print_warning "Crop system status endpoint not responding"
    fi

    # Test Flower monitoring
    if curl -f http://admin:admin@localhost:5555 &> /dev/null; then
        print_success "Flower monitoring is available"
    else
        print_warning "Flower monitoring not responding"
    fi

    print_success "Deployment test completed"
}

# Function to show service status
show_status() {
    print_status "Service Status:"
    echo ""

    # Show Docker Compose status
    docker-compose -f $DOCKER_COMPOSE_FILE ps

    echo ""
    print_status "Available Endpoints:"
    echo "  🌐 API: http://localhost:8090"
    echo "  🌸 Flower: http://localhost:5555 (admin:admin)"
    echo "  📊 Health: http://localhost:8090/health"
    echo "  🎯 Crop Status: http://localhost:8090/crop/status"
    echo "  📝 API Docs: http://localhost:8090/docs"

    echo ""
    print_status "Useful Commands:"
    echo "  📋 View logs: docker-compose logs -f [service_name]"
    echo "  🔄 Restart: docker-compose restart [service_name]"
    echo "  🛑 Stop all: docker-compose down"
    echo "  🧪 Test crop: docker-compose exec social-media-api python test_crop_system.py"
}

# Function to download SAM checkpoint manually
download_sam() {
    print_status "Downloading SAM checkpoints manually..."

    # Run the SAM downloader service
    docker-compose -f $DOCKER_COMPOSE_FILE --profile setup run --rm sam-downloader

    print_success "SAM checkpoint download completed"
}

# Function to show help
show_help() {
    echo "Social Media Publisher with Intelligent Cropping - Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start       Start all services (default)"
    echo "  stop        Stop all services"
    echo "  restart     Restart all services"
    echo "  status      Show service status"
    echo "  logs        Show logs for all services"
    echo "  test        Test the deployment"
    echo "  sam         Download SAM checkpoints manually"
    echo "  clean       Clean up containers and volumes"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start           # Start all services"
    echo "  $0 logs api        # Show API logs"
    echo "  $0 test            # Test deployment"
    echo "  $0 sam             # Download SAM models"
}

# Main script logic
case "${1:-start}" in
    "start")
        print_status "🚀 Starting Social Media Publisher with Intelligent Cropping..."
        check_requirements
        check_env_file
        setup_sam_checkpoints
        start_services
        test_deployment
        show_status
        print_success "🎉 Deployment completed successfully!"
        ;;

    "stop")
        print_status "Stopping all services..."
        docker-compose -f $DOCKER_COMPOSE_FILE down
        print_success "All services stopped"
        ;;

    "restart")
        print_status "Restarting all services..."
        docker-compose -f $DOCKER_COMPOSE_FILE restart
        print_success "All services restarted"
        ;;

    "status")
        show_status
        ;;

    "logs")
        if [ -n "$2" ]; then
            docker-compose -f $DOCKER_COMPOSE_FILE logs -f "social-media-$2"
        else
            docker-compose -f $DOCKER_COMPOSE_FILE logs -f
        fi
        ;;

    "test")
        test_deployment
        ;;

    "sam")
        download_sam
        ;;

    "clean")
        print_warning "This will remove all containers and volumes. Are you sure? [y/N]"
        read -r confirmation
        if [[ $confirmation =~ ^[Yy]$ ]]; then
            docker-compose -f $DOCKER_COMPOSE_FILE down -v
            docker system prune -f
            print_success "Cleanup completed"
        else
            print_status "Cleanup cancelled"
        fi
        ;;

    "help"|"-h"|"--help")
        show_help
        ;;

    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac