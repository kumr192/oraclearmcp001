FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY server.py .

# Install dependencies with uv
RUN uv sync --no-dev

# Railway sets PORT env var
ENV PORT=8000

# Run the server
CMD ["uv", "run", "python", "server.py"]
