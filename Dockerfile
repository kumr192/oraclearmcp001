FROM python:3.12-slim

WORKDIR /app

COPY server.py ./

RUN pip install "mcp[cli]>=1.8.0" httpx pydantic uvicorn starlette

ENV PORT=8000

CMD ["python", "server.py"]
