# ── Stage 1: dependency builder ───────────────────────────────────────────────
# Build context must be the repository root so we can COPY src/shared/.
# GitHub Actions calls: docker build -f src/api/Dockerfile .
FROM python:3.12-slim AS builder

WORKDIR /build
COPY src/api/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Azure Roadmap Agent — API"
LABEL org.opencontainers.image.description="FastAPI service that serves Azure roadmap data to the Copilot Agent"
LABEL org.opencontainers.image.source="https://github.com/GITHUB_USERNAME/azure-roadmap-agent"

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

WORKDIR /app

# Shared library → exposed as the 'services' package inside the API
COPY src/shared/ ./services/

# API source
COPY src/api/main.py .
COPY src/api/routers/ ./routers/
# services/__init__.py is already created; keep it
COPY src/api/services/__init__.py ./services/__init__.py

# Non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", \
     "--workers", "2", "--log-level", "info"]
