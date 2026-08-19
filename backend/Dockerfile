# --- Builder stage ---------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Runtime stage -----------------------------------------------------------
FROM python:3.12-slim

RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings

COPY . .
RUN chown -R appuser:appuser /app

USER appuser

RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '8000') + '/api/v1/health/')" || exit 1

# Shell form (not exec-form JSON array) so $PORT actually expands - Railway
# (and most container platforms) inject a dynamic PORT env var at runtime
# and expect the app to bind to it; falls back to 8000 for docker-compose/
# local use where PORT is unset.
CMD gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 4 --threads 2 --timeout 60
