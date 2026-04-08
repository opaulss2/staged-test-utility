pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
    }

    environment {
        TPMS_DLT_HOST = '127.0.0.1'
        TPMS_DLT_PORT = '3491'
        TPMS_SWUT_MOCK_URL = 'http://127.0.0.1:8082'
        TPMS_SSH_MOCK_URL = 'http://127.0.0.1:8081'
        TPMS_TEST_DURATION_SECONDS = '5'
        TPMS_SHORTENED_DURATION_SECONDS = '2'
        PERF_ITERATIONS = '10'
        PERF_STAGES = '0,1,3,4'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Preflight') {
            steps {
                sh '''
                    set -euo pipefail
                    python3 --version
                    docker --version
                    docker compose version
                '''
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    set -euo pipefail
                    python3 -m pip install --upgrade pip
                    python3 -m pip install -e . --no-deps
                '''
            }
        }

        stage('Compile Check') {
            steps {
                sh '''
                    set -euo pipefail
                    python3 -m compileall tpms_utility tools
                '''
            }
        }

        stage('Start Mock Stack') {
            steps {
                sh '''
                    set -euo pipefail
                    docker compose -f docker-compose.mock.yml up -d
                '''
            }
        }

        stage('Run Stage Latency Benchmark') {
            steps {
                sh '''
                    set -euo pipefail
                    mkdir -p output/perf
                    python3 tools/perf/run_stage_latency.py \
                        --iterations "${PERF_ITERATIONS}" \
                        --stages "${PERF_STAGES}" \
                        --output output/perf/stage_latency.json
                '''
            }
        }

        stage('Summarize Metrics') {
            steps {
                sh '''
                    set -euo pipefail
                    python3 - <<'PY'
import json
from pathlib import Path

report = Path('output/perf/stage_latency.json')
if not report.exists():
    raise SystemExit('Missing stage latency report')

data = json.loads(report.read_text(encoding='utf-8'))
print('Stage latency summary (ms):')
for stage, stats in sorted(data.get('summary_ms', {}).items(), key=lambda item: int(item[0])):
    print(
        f"stage {stage}: avg={stats['avg_ms']:.3f}, min={stats['min_ms']:.3f}, max={stats['max_ms']:.3f}, count={int(stats['count'])}"
    )
PY
                '''
            }
        }
    }

    post {
        always {
            sh '''
                set +e
                mkdir -p output/perf
                docker compose -f docker-compose.mock.yml logs > output/perf/mock_services.log 2>&1
                docker compose -f docker-compose.mock.yml down -v --remove-orphans
                exit 0
            '''
            archiveArtifacts artifacts: 'output/perf/*.json,output/perf/*.log', allowEmptyArchive: true
        }
    }
}
