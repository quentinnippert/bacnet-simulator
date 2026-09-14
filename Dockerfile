FROM ghcr.io/astral-sh/uv:0.12.13 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src/ src/
COPY config/ config/
RUN uv sync --frozen --no-dev --no-editable \
    && useradd --system --uid 10001 --create-home lab \
    && mkdir -p /app/data && chown lab:lab /app/data
USER lab
ENV PATH="/app/.venv/bin:$PATH" BACNET_LAB_DB_PATH=/app/data/bacnet_lab.db
EXPOSE 8080
CMD ["python", "-m", "bacnet_lab"]
