# ── Stage 1: dependency builder ───────────────────────────────────────────────
# Build context must be the repository root.
# GitHub Actions calls: docker build -f src/scheduler/Dockerfile .
FROM python:3.12-slim AS builder

WORKDIR /build
COPY src/scheduler/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ── Stage 2: lean runtime image ───────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.title="Azure Roadmap Agent — Scheduler"
LABEL org.opencontainers.image.description="CronJob that sends the weekly Azure roadmap digest email"
LABEL org.opencontainers.image.source="https://github.com/GITHUB_USERNAME/azure-roadmap-agent"

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

WORKDIR /app

# Shared library + scheduler script both land at /app root
COPY src/shared/ .
COPY src/scheduler/send_digest.py .

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

CMD ["python", "send_digest.py"]
