FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --no-install-project

COPY app ./app
COPY scripts ./scripts
COPY docker-entrypoint.sh ./
RUN uv sync && chmod +x docker-entrypoint.sh

ENV BDPM_DATA_DIR=/app/data \
    PORT=8090

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD uv run python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8090\")}/health', timeout=3).status == 200 else 1)"

ENTRYPOINT ["./docker-entrypoint.sh"]
