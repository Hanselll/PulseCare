FROM public.ecr.aws/docker/library/python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/libs/pulsecare-core

WORKDIR /app

COPY libs/pulsecare-core /app/libs/pulsecare-core
COPY services/ingestion-service/requirements.txt /app/services/ingestion-service/requirements.txt
RUN pip install --no-cache-dir -r /app/services/ingestion-service/requirements.txt

COPY services/ingestion-service/app /app/services/ingestion-service/app
WORKDIR /app/services/ingestion-service

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
