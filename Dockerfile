# ===========================================
# Translation Agent System - Dockerfile
# ===========================================
# Multi-stage build for Python backend + React frontend
# Uses UV for fast, deterministic Python dependency management

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build

# Stage 2: Python runtime
FROM python:3.13-slim AS backend

WORKDIR /app

# Install system dependencies, gosu (for user switching), and UV
RUN apt-get update && apt-get install -y \
    curl \
    gosu \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (for layer caching)
COPY pyproject.toml uv.lock ./

# Install Python dependencies using UV
# --frozen: Use exact versions from uv.lock
# --no-dev: Skip development dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY config/ ./config/
COPY backend/ ./backend/
COPY agent/ ./agent/
COPY main.py ./

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose application port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Entrypoint handles directory permissions and user switching
ENTRYPOINT ["/entrypoint.sh"]

# Run the application using UV (uses venv created by uv sync)
CMD ["uv", "run", "python", "main.py"]
