FROM python:3.11-slim

# psycopg2-binary : Postgres 백엔드 스토어
# boto3           : R2(S3 호환) artifact 저장소
#
# [auth] extra 는 필수다. 빼면 `--app-name basic-auth` 가 Flask-WTF(CSRF) 부재로
# ImportError 를 내고 컨테이너가 crash-loop 한다.
# (다행히 인증 없이 뜨지는 않는다 — fail-closed 확인함)
#
# 버전은 정확히 고정한다. 로컬 스택 검증을 통과한 버전이며,
# 재현성 평가에서 환경을 되살릴 수 있어야 한다.
RUN pip install --no-cache-dir \
        "mlflow[auth]==3.15.1" \
        psycopg2-binary \
        boto3

WORKDIR /app
EXPOSE 5000
