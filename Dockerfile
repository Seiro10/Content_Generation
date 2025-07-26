# Social Media Publisher - Main Application with Intelligent Cropping
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OpenCV, SAM and existing requirements
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gcc \
    g++ \
    build-essential \
    libpq-dev \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libxshmfence1 \
    python3-dev \
    pkg-config \
    # OpenCV dependencies
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libgstreamer-plugins-base1.0-0 \
    # Image processing dependencies
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libhdf5-dev \
    libopenblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    gfortran \
    # Additional tools
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install dependencies in stages to handle potential issues
# Stage 1: Core dependencies (most stable)
RUN pip install --no-cache-dir \
    numpy \
    pillow \
    opencv-python-headless \
    scikit-image \
    matplotlib \
    requests \
    && echo "✅ Core image processing dependencies installed"

# Stage 2: PyTorch (can be problematic)
RUN pip install --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    || pip install --no-cache-dir torch torchvision \
    || echo "⚠️ PyTorch installation failed, SAM will not be available"

# Stage 3: Main application dependencies
RUN pip install --no-cache-dir \
    fastapi uvicorn \
    celery redis \
    boto3 \
    psycopg2-binary \
    langchain langchain-anthropic \
    langgraph \
    pydantic pydantic-settings \
    && echo "✅ Main application dependencies installed"

# Stage 4: Remaining dependencies
RUN pip install --no-cache-dir \
    anthropic \
    python-multipart \
    python-dotenv \
    requests-oauthlib \
    gunicorn \
    alembic \
    flower \
    && echo "✅ Remaining dependencies installed" \
    || echo "⚠️ Some optional dependencies failed"

# Stage 5: SAM (Segment Anything Model) - Optional
RUN pip install --no-cache-dir git+https://github.com/facebookresearch/segment-anything.git \
    && echo "✅ SAM installed successfully" \
    || echo "⚠️ SAM installation failed, will use OpenCV-only fallback"

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy application code
COPY app/ ./app/
COPY test_*.py ./
COPY *.md ./

# Create necessary directories
RUN mkdir -p /app/logs /app/temp /app/data /app/output /app/models/sam_checkpoints

# Download SAM checkpoints (optional - can be done at runtime)
# Uncomment the line below to download SAM checkpoint at build time (increases image size by ~360MB)
# RUN wget -O /app/models/sam_checkpoints/sam_vit_b_01ec64.pth https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth || echo "SAM checkpoint download failed"

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8090/health || exit 1

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]

# Default command (API service)
CMD ["api"]