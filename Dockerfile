# ----------- Build Stage -----------
    FROM python:3.11-slim as builder

    ARG BUILD_DATE
    ARG VERSION
    ARG VCS_REF
    
    LABEL maintainer="sarun.m@aitechindia.com" \
          org.opencontainers.image.title="ML Model API" \
          org.opencontainers.image.description="Production ML model serving API" \
          org.opencontainers.image.version=${VERSION} \
          org.opencontainers.image.created=${BUILD_DATE} \
          org.opencontainers.image.revision=${VCS_REF} \
          org.opencontainers.image.source="https://github.com/sarun888/health-check.git"
    
    # Install build dependencies
    RUN apt-get update && apt-get install -y \
        build-essential \
        gcc \
        && rm -rf /var/lib/apt/lists/* \
        && apt-get clean
    
    # Create virtual environment
    RUN python -m venv /opt/venv
    ENV PATH="/opt/venv/bin:$PATH"
    
    # Install Python dependencies
    COPY requirements.txt .
    RUN pip install --no-cache-dir --upgrade pip && \
        pip install --no-cache-dir -r requirements.txt
    
    # ----------- Production Stage -----------
    FROM python:3.11-slim as production
    
    # Runtime dependencies
    RUN apt-get update && apt-get install -y \
        curl \
        && rm -rf /var/lib/apt/lists/* \
        && apt-get clean
    
    # Create non-root user
    RUN groupadd -r appuser && useradd -r -g appuser appuser
    
    # Copy virtualenv from builder
    COPY --from=builder /opt/venv /opt/venv
    ENV PATH="/opt/venv/bin:$PATH"
    
    # Set work directory
    WORKDIR /app
    
    # Copy application code
    COPY --chown=appuser:appuser app.py gunicorn_config.py ./
    
    # Pre-create necessary folders and fix permissions
    RUN mkdir -p /app/models /app/logs && \
        chown -R appuser:appuser /app
    
    # Switch to non-root user
    USER appuser
    
    # Expose the correct port (Azure ML expects 5001)
    EXPOSE 5001
    ENV PORT=5001
    
    # Health check
    HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
        CMD curl -f http://localhost:5001/health || exit 1
    
    # Final env flags
    ENV PYTHONUNBUFFERED=1
    ENV PYTHONDONTWRITEBYTECODE=1
    ENV FLASK_ENV=production
    
    # Launch via Gunicorn
    CMD ["gunicorn", "--config", "gunicorn_config.py", "--bind", "0.0.0.0:5001", "app:app"]
    