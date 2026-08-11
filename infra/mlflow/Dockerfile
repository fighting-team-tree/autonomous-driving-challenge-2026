FROM python:3.11-slim

# psycopg2-binary : Postgres 백엔드 스토어
# boto3           : R2(S3 호환) artifact 저장소
#
# mlflow 버전은 major만 고정해 두었다. VM에서 첫 기동에 성공하면
# `docker compose exec mlflow pip freeze | grep -i mlflow` 로 확인한 정확한 버전으로
# 아래를 고정하는 것을 권장한다 (재현성 평가 대비).
RUN pip install --no-cache-dir \
        "mlflow>=3.1,<4" \
        psycopg2-binary \
        boto3

WORKDIR /app
EXPOSE 5000
