FROM python:3.12-slim

WORKDIR /app

# Install poetry
RUN pip install poetry==1.8.3

# Copy dependency files first for layer caching
COPY pyproject.toml ./

# Install dependencies (no dev)
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy source
COPY src/ ./src/
COPY config/ ./config/

# Non-root user
RUN useradd -m -u 1001 opsflow
USER opsflow

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "ringsnap_ops_flow.main:app", "--host", "0.0.0.0", "--port", "8080"]
