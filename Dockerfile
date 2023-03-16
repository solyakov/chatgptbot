FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --upgrade pip

COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY bot ./bot

RUN groupadd -r appuser && useradd -r -g appuser -u 1001 -m appuser \
    && chown -R appuser:appuser /app

USER appuser

CMD ["python", "-m", "bot"]
