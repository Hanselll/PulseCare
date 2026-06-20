FROM public.ecr.aws/docker/library/python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/libs/pulsecare-core

WORKDIR /app

COPY libs/pulsecare-core /app/libs/pulsecare-core
COPY services/device-simulator/requirements.txt /app/services/device-simulator/requirements.txt
RUN pip install --no-cache-dir -r /app/services/device-simulator/requirements.txt

COPY services/device-simulator/app /app/services/device-simulator/app
WORKDIR /app/services/device-simulator

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
