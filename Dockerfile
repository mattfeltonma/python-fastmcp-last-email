FROM python:3.14-slim

RUN pip install --no-cache-dir uv

ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install dependencies before code so this layer can be reused when app code changes
COPY src/pyproject.toml src/uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/server.py ./server.py

EXPOSE 80

CMD ["python", "server.py"]
