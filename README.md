# PulseCare MVP

PulseCare is a cloud-native diagnostic target system for remote device health monitoring.
The first version runs locally with Docker Compose and focuses on a simple but observable
microservice chain.

## MVP Services

```text
device-simulator
  -> ingestion-service
  -> risk-scoring-service
  -> alert-service
```

Dependencies:

- PostgreSQL stores device signals, risk scores, and alerts.
- Redis stores recent device state and alert deduplication keys.
- Prometheus scrapes service metrics.
- Grafana provides a starter dashboard.

## Run Locally

```powershell
docker compose -f deploy/docker-compose.yml up --build
```

Useful URLs:

- Ingestion API: <http://localhost:8000>
- Risk scoring API: <http://localhost:8001>
- Alert API: <http://localhost:8002>
- Simulator health/metrics: <http://localhost:8003>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000> with `admin` / `admin`
- PulseCare Console: <http://localhost:8080>

The frontend is served by the `frontend` Docker Compose service. It reads service
health, alert records, and Prometheus metrics through the bundled nginx proxy, so
it runs without a separate Node.js build step.

## Manual Signal

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/api/v1/signals `
  -ContentType "application/json" `
  -Body '{
    "device_id": "dev-001",
    "timestamp": "2026-05-18T08:00:00Z",
    "temperature": 85.0,
    "voltage": 2.8,
    "heartbeat": true,
    "error_code": "E_OVERHEAT",
    "region": "gz-edge-1",
    "firmware_version": "1.0.3"
  }'
```

## Runtime Modes

Change `ERROR_MODE` in `deploy/docker-compose.yml` for the simulator:

- `normal`
- `overheat`
- `low_voltage`
- `heartbeat_loss`
- `invalid_schema`
- `traffic_spike`
- `batch_offline`

Fault switches:

- `MEMORY_LEAK_MODE=true` on `risk-scoring-service`
- `SCORING_DELAY_MS=500` on `risk-scoring-service`
- `REDIS_LATENCY_MS=500` on `risk-scoring-service` or `alert-service`

## Tests

```powershell
py -m pip install -e libs/pulsecare-core pytest
py -m pytest
```

## Local Jenkins

Jenkins runs as a separate Docker Compose project so it does not conflict with
the PulseCare stack.

```powershell
docker compose -f deploy/jenkins-compose.yml up -d --build
```

Useful URLs:

- Jenkins: <http://localhost:8090>
- Jenkins agent port: `50000`

The Jenkins container mounts the project at `/workspace` and the host Docker
socket at `/var/run/docker.sock`. The bundled `PulseCare-Local-CI` pipeline runs
unit tests, validates the PulseCare Compose file, builds service images, starts
the stack, and checks service health.
