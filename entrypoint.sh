#!/bin/bash
# entrypoint.sh - Social Media Publisher with Intelligent Cropping

set -e

# Function to check if SAM checkpoint exists and download if needed
download_sam_checkpoint() {
    if [ "$SAM_ENABLED" = "true" ] && [ ! -f "/app/models/sam_checkpoints/sam_vit_b_01ec64.pth" ]; then
        echo "🤖 SAM enabled but checkpoint not found. Downloading..."
        mkdir -p /app/models/sam_checkpoints

        if [ "$SAM_MODEL_TYPE" = "vit_l" ]; then
            echo "📥 Downloading SAM ViT-L checkpoint (1.2GB)..."
            wget -O /app/models/sam_checkpoints/sam_vit_l_0b3195.pth \
                https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth || \
                echo "❌ SAM ViT-L download failed, will use fallback"
        elif [ "$SAM_MODEL_TYPE" = "vit_h" ]; then
            echo "📥 Downloading SAM ViT-H checkpoint (2.4GB)..."
            wget -O /app/models/sam_checkpoints/sam_vit_h_4b8939.pth \
                https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth || \
                echo "❌ SAM ViT-H download failed, will use fallback"
        else
            echo "📥 Downloading SAM ViT-B checkpoint (358MB)..."
            wget -O /app/models/sam_checkpoints/sam_vit_b_01ec64.pth \
                https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth || \
                echo "❌ SAM ViT-B download failed, will use fallback"
        fi

        if [ -f "/app/models/sam_checkpoints/sam_vit_b_01ec64.pth" ] ||
           [ -f "/app/models/sam_checkpoints/sam_vit_l_0b3195.pth" ] ||
           [ -f "/app/models/sam_checkpoints/sam_vit_h_4b8939.pth" ]; then
            echo "✅ SAM checkpoint downloaded successfully"
        else
            echo "⚠️ SAM checkpoint download failed, using OpenCV-only fallback"
            export SAM_ENABLED=false
        fi
    fi
}

# Function to test crop system
test_crop_system() {
    echo "🧪 Testing intelligent crop system..."
    python -c "
try:
    import cv2
    import numpy as np
    from PIL import Image
    print('✅ OpenCV + PIL available')

    try:
        from segment_anything import sam_model_registry
        print('✅ SAM available')
    except ImportError:
        print('⚠️ SAM not available, using OpenCV fallback')

    from app.services.unified_cropper import unified_cropper
    if unified_cropper is None:
        print('❌ Unified cropper not initialized')
        exit(1)

    status = unified_cropper.get_status()
    primary_method = status.get('primary_method', 'unknown')
    print(f'✅ Unified cropper initialized: {primary_method}')

except Exception as e:
    print(f'❌ Crop system test failed: {e}')
    exit(1)
"
    echo "✅ Crop system test passed"
}

# Wait for dependencies
wait_for_redis() {
    echo "⏳ Waiting for Redis..."
    while ! timeout 1 bash -c "echo > /dev/tcp/social-media-redis/6379" 2>/dev/null; do
        sleep 1
    done
    echo "✅ Redis is ready"
}

# Main execution
case "$1" in
    "api")
        echo "🚀 Starting Social Media Publisher API with Intelligent Cropping..."
        download_sam_checkpoint
        wait_for_redis
        test_crop_system
        exec uvicorn app.main:app --host 0.0.0.0 --port 8090 --workers 1
        ;;

    "worker-content")
        echo "👷 Starting Content Generation Worker..."
        wait_for_redis
        exec celery -A app.services.celery_app worker \
            --loglevel=info \
            --queues=content_generation \
            --hostname=content-worker@%h \
            --concurrency=2 \
            --max-tasks-per-child=1000
        ;;

    "worker-publishing")
        echo "📤 Starting Publishing Worker..."
        wait_for_redis
        exec celery -A app.services.celery_app worker \
            --loglevel=info \
            --queues=content_publishing \
            --hostname=publishing-worker@%h \
            --concurrency=2 \
            --max-tasks-per-child=1000
        ;;

    "worker-image")
        echo "🎨 Starting Image Processing Worker with Intelligent Cropping..."
        download_sam_checkpoint
        wait_for_redis
        test_crop_system
        exec celery -A app.services.celery_app worker \
            --loglevel=info \
            --queues=image_generation,image_optimization,intelligent_cropping \
            --hostname=image-worker@%h \
            --concurrency=1 \
            --max-tasks-per-child=100 \
            --pool=threads
        ;;

    "worker-formatting")
        echo "✍️ Starting Content Formatting Worker..."
        wait_for_redis
        exec celery -A app.services.celery_app worker \
            --loglevel=info \
            --queues=content_formatting \
            --hostname=formatting-worker@%h \
            --concurrency=2 \
            --max-tasks-per-child=1000
        ;;

    "beat")
        echo "⏰ Starting Celery Beat Scheduler..."
        wait_for_redis
        exec celery -A app.services.celery_app beat --loglevel=info
        ;;

    "flower")
        echo "🌸 Starting Flower Monitoring..."
        wait_for_redis
        exec celery -A app.services.celery_app flower \
            --port=5555 \
            --basic-auth=admin:admin
        ;;

    "test-crop")
        echo "🧪 Running Crop System Tests..."
        download_sam_checkpoint
        test_crop_system
        exec python test_crop_system.py
        ;;

    "shell")
        echo "🐚 Starting Interactive Shell..."
        exec /bin/bash
        ;;

    *)
        echo "❌ Unknown command: $1"
        echo "Available commands:"
        echo "  api              - Start FastAPI application"
        echo "  worker-content   - Start content generation worker"
        echo "  worker-publishing - Start publishing worker"
        echo "  worker-image     - Start image processing worker (with intelligent cropping)"
        echo "  worker-formatting - Start content formatting worker"
        echo "  beat             - Start Celery beat scheduler"
        echo "  flower           - Start Flower monitoring"
        echo "  test-crop        - Test intelligent cropping system"
        echo "  shell            - Interactive shell"
        exit 1
        ;;
esac