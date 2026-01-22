FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

WORKDIR /app

COPY pyproject.toml server.py ./

RUN uv pip install --system -r pyproject.toml

ENV PORT=8000

CMD ["python", "server.py"]
