FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends zlib1g libexpat1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p logs data static

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/       ./core/
COPY models/     ./models/
COPY api/        ./api/
COPY services/   ./services/
COPY static/     ./static/
COPY data/       ./data/
COPY main.py     .

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:80/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
