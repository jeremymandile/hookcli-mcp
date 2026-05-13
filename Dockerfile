FROM python:3.12-slim AS builder
WORKDIR /app

# Copy full source first so editable install resolves package metadata
COPY . .
RUN pip install --no-cache-dir --user -e .

FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r app && useradd -r -g app app
COPY --from=builder /root/.local /home/app/.local
COPY --from=builder /app /app
ENV PATH="/home/app/.local/bin:$PATH"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1
USER app
CMD ["uvicorn", "hookcli_mcp.server:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--log-level", "info"]
