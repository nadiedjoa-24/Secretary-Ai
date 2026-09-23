FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEMO_MODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY secretary_ai secretary_ai
COPY web web
COPY planning_json planning_json

RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000

# One worker: conversations and rate limits are kept in memory.
CMD gunicorn --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:${PORT:-8000} web.app:app
