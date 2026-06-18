FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/libs/pulsecare-core

WORKDIR /app

COPY libs/pulsecare-core /app/libs/pulsecare-core
COPY services/alert-service/requirements.txt /app/services/alert-service/requirements.txt
RUN pip install --no-cache-dir -r /app/services/alert-service/requirements.txt

COPY services/alert-service/app /app/services/alert-service/app
WORKDIR /app/services/alert-service

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
