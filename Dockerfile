FROM python:3.12-slim AS builder
WORKDIR /app

# Copy full source so editable install resolves package metadata
COPY . .
# Install globally (not --user) so any runtime user can access packages
RUN pip install --no-cache-dir -e .

FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r app && useradd -r -g app app
# Copy globally installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Run as root in dev (Docker socket access). Use docker-socket-proxy for production.
CMD ["uvicorn", "hookcli_mcp.server:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--log-level", "info"]
