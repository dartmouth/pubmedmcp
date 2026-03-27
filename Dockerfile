# Stage 1: Build dependencies with uv
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install dependencies (no dev deps) into a virtual environment
# --no-editable ensures the package is copied into site-packages
# rather than symlinked, so the runtime stage doesn't need src/
RUN uv sync --frozen --no-dev --no-editable

# Stage 2: Minimal runtime image
FROM python:3.12-slim

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Put the venv on PATH so the installed entrypoint is available
ENV PATH="/app/.venv/bin:$PATH"

# Default to streamable-http transport for container deployments
ENV TRANSPORT=streamable-http
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

# Run the MCP server
CMD ["pubmedmcp"]
