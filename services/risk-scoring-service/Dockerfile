FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/libs/pulsecare-core

WORKDIR /app

COPY libs/pulsecare-core /app/libs/pulsecare-core
COPY services/risk-scoring-service/requirements.txt /app/services/risk-scoring-service/requirements.txt
RUN pip install --no-cache-dir -r /app/services/risk-scoring-service/requirements.txt

COPY services/risk-scoring-service/app /app/services/risk-scoring-service/app
WORKDIR /app/services/risk-scoring-service

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
