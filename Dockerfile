# Multi-stage Dockerfile for Hansard MCP Server
# Optimized for Cloud Run deployment

FROM python:3.11-slim as builder

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml setup.py ./
COPY src/ ./src/

# Install dependencies
RUN uv pip install --system --no-cache .

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN pip install --no-cache-dir uv && \
    apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 mcp && \
    mkdir -p /app && \
    chown -R mcp:mcp /app

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code, scripts, and data
COPY --chown=mcp:mcp src/ ./src/
COPY --chown=mcp:mcp scripts/ ./scripts/
COPY --chown=mcp:mcp data/ ./data/

# Switch to non-root user
USER mcp

# Set Python path
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Expose port (Cloud Run uses PORT env var)
EXPOSE 8080

# Start FastMCP server with uvicorn (HTTP mode for Cloud Run)
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8080}"]
