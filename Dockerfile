# ============================================
# Stage 1: Build environment
# ============================================
FROM python:3.13-slim AS build

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Build optimizations
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy dependency files (leverage layer caching)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies separately (better caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

# Copy application code
COPY src ./src
COPY scripts ./scripts
COPY data ./data
COPY populate_hansard_speeches.py populate_job.py drop_table_job.py ./

# Install project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ============================================
# Stage 2: Runtime environment
# ============================================
FROM python:3.13-slim AS runtime

# Create non-root user (UID 1000 for security)
RUN useradd --uid 1000 --create-home --shell /bin/bash appuser

# Runtime environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
RUN chown -R appuser:appuser /app

# Copy virtual environment from build stage
COPY --from=build --chown=appuser:appuser /app /app

# Switch to non-root user
USER appuser

# Expose Cloud Run port
EXPOSE 8080

# Health check (using Python's built-in urllib for simplicity)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health').read()"

# Start FastMCP server in HTTP mode for Cloud Run
# Use the ASGI app exposed in server.py
CMD ["sh", "-c", "uvicorn src.server:app --host 0.0.0.0 --port ${PORT:-8080} --app-dir /app"]
