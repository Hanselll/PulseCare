pipeline {
  agent any
  options {
    timestamps()
    disableConcurrentBuilds()
  }
  environment {
    PULSECARE_ROOT = "${env.PULSECARE_WORKSPACE ?: '/workspace'}"
    COMPOSE_FILE_PATH = "${env.PULSECARE_WORKSPACE ?: '/workspace'}/deploy/docker-compose.yml"
    COMPOSE_CMD = "docker-compose"
  }
  stages {
    stage('Unit Tests') {
      steps {
        dir("${env.PULSECARE_ROOT}") {
          sh '''
            set -eu
            python3 -m venv /tmp/pulsecare-ci-venv
            . /tmp/pulsecare-ci-venv/bin/activate
            python -m pip install --upgrade pip
            python -m pip install -e libs/pulsecare-core pytest
            python -m pytest
          '''
        }
      }
    }

    stage('Compose Config') {
      steps {
        sh '$COMPOSE_CMD -f "$COMPOSE_FILE_PATH" config >/tmp/pulsecare-compose-config.yml'
      }
    }

    stage('Build Images') {
      steps {
        sh '$COMPOSE_CMD -f "$COMPOSE_FILE_PATH" build'
      }
    }

    stage('Start Stack') {
      steps {
        sh '$COMPOSE_CMD -f "$COMPOSE_FILE_PATH" up -d'
      }
    }

    stage('Health Checks') {
      steps {
        sh '''
          set -eu
          check_service() {
            service="$1"
            path="$2"
            $COMPOSE_CMD -f "$COMPOSE_FILE_PATH" exec -T "$service" python - <<PY
import json
import urllib.request

url = "http://127.0.0.1:8000${path}"
with urllib.request.urlopen(url, timeout=10) as response:
    payload = response.read().decode("utf-8")
    print("${service}", response.status, payload)
    if response.status != 200:
        raise SystemExit(1)
PY
          }

          check_service ingestion-service /healthz
          check_service risk-scoring-service /healthz
          check_service alert-service /healthz
          check_service device-simulator /healthz
          $COMPOSE_CMD -f "$COMPOSE_FILE_PATH" exec -T frontend wget -qO- http://127.0.0.1 >/tmp/pulsecare-frontend.html
          test -s /tmp/pulsecare-frontend.html
        '''
      }
    }
  }
  post {
    always {
      sh '$COMPOSE_CMD -f "$COMPOSE_FILE_PATH" ps || true'
    }
    failure {
      sh '$COMPOSE_CMD -f "$COMPOSE_FILE_PATH" logs --no-color --tail=200 || true'
      archiveArtifacts artifacts: '/tmp/pulsecare-compose-config.yml', allowEmptyArchive: true
    }
  }
}
