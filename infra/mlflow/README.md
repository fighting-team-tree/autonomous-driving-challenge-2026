# MLflow 트래킹 서버

클라우드 VM에 올리는 팀 공용 MLflow. 설정을 코드로 관리해서 언제든 재구축할 수 있게 한다.

```
caddy (자동 HTTPS)  →  mlflow (내장 basic-auth)  →  postgres (백엔드 스토어)
                                 ↓
                          R2 (artifact, 서버가 대리 전송)
```

> ✅ **로컬에서 전 구간 검증 완료** (2026-08-11, Docker 29.5.3 / Compose v5.1.4).
> R2 자리에 MinIO를 세워 컨테이너 기동 → HTTPS → 인증 차단 → run 기록 →
> artifact 오브젝트 스토리지 안착까지 확인했습니다. 검증에 쓴 하네스는
> `compose.test.yml` 로 남겨뒀습니다.
>
> 다만 **실제 VM에서의 Let's Encrypt 발급은 확인하지 못했습니다** (로컬은 Caddy
> 내부 CA를 씁니다). 첫 배포자가 아래 "검증" 절을 실행해주세요.

## 왜 이렇게 구성했나

**인증이 핵심입니다.** MLflow 서버는 기본적으로 인증이 없습니다. 그냥 노출하면
누구나 우리 실험 지표·하이퍼파라미터·seed를 읽을 수 있고, 그러면
[D-002](https://fighting-team-tree.github.io/autonomous-driving-challenge-2026/decisions/)의
전제가 무너집니다 — 문서에서 일부러 숨긴 값을 MLflow UI에서 그대로 보게 됩니다.
경쟁팀이 165개이고, 주최측이 작년에 "split 시드까지 동일"로 팀을 적발했습니다.

| 선택 | 이유 |
|---|---|
| **Postgres** (SQLite 아님) | 4명이 동시에 학습을 돌리면 SQLite는 `database is locked`가 난다 |
| **Caddy + HTTPS** | basic auth 자격증명은 base64 평문이다. Colab에서 접속하면 공용 경로를 지난다 |
| **`--artifacts-destination`** | 서버가 R2로 대리 전송한다 → **클라이언트에 R2 쓰기 키를 안 뿌려도 된다** |
| **sslip.io** | `<VM_IP>.sslip.io`가 그 IP로 해석되고 Let's Encrypt도 발급된다. 도메인 구매 불필요 |

## 배포

VM에서:

```bash
git clone https://github.com/fighting-team-tree/autonomous-driving-challenge-2026.git
cd autonomous-driving-challenge-2026/infra/mlflow

cp .env.example .env
cp basic_auth.ini.example basic_auth.ini
# 두 파일을 채운다. 둘 다 .gitignore 되어 있다.

docker compose up -d --build
docker compose logs -f mlflow
```

방화벽에서 **80, 443**을 열어야 합니다. 80은 Let's Encrypt 인증에 필요합니다.

### 팀원 계정 추가

관리자 계정으로 만듭니다. 서버가 뜬 뒤:

```python
from mlflow.server.auth.client import AuthServiceClient

c = AuthServiceClient("https://<MLFLOW_HOSTNAME>")
# 관리자 자격증명은 환경변수로
#   export MLFLOW_TRACKING_USERNAME=... MLFLOW_TRACKING_PASSWORD=...
c.create_user(username="ashrate", password="...")
```

비밀번호는 각자에게 **채팅이 아닌 경로**로 전달하고, 받은 사람이 바로 바꾸게 합니다.

## 검증 (처음 띄운 사람이 확인해주세요)

```bash
# 1. 컨테이너 3개가 모두 healthy/running 인가
docker compose ps

# 2. HTTPS 인증서가 발급됐나 (200 또는 401 이 나와야 정상)
curl -sI https://<MLFLOW_HOSTNAME> | head -3

# 3. 인증 없이는 막히는가 — 401 이 나와야 한다. 200 이면 설정이 잘못된 것
curl -s -o /dev/null -w '%{http_code}\n' https://<MLFLOW_HOSTNAME>/api/2.0/mlflow/experiments/search

# 4. 인증하면 되는가
curl -s -u "$USER:$PASS" https://<MLFLOW_HOSTNAME>/api/2.0/mlflow/experiments/search | head -c 200

# 5. 실제 버전 확인 → Dockerfile 에 정확히 고정
docker compose exec mlflow pip freeze | grep -i '^mlflow'
```

**3번이 200이면 즉시 중단하고 `basic_auth.ini`의 `default_permission`을 확인하세요.**
`NO_PERMISSIONS`가 아니면 익명 접근이 열립니다.

## 클라이언트에서 쓰기

저장소 루트의 `.env`를 씁니다 (이 디렉터리의 `.env`가 아닙니다).

```bash
MLFLOW_TRACKING_URI=https://<MLFLOW_HOSTNAME>
MLFLOW_TRACKING_USERNAME=<본인 계정>
MLFLOW_TRACKING_PASSWORD=<본인 비번>
```

```python
import mlflow, os

mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
mlflow.set_experiment("prediction")          # planning | prediction | e2e

with mlflow.start_run(run_name="EXP-M003-shared-decoder"):
    mlflow.set_tag("exp_id", "EXP-M003")     # 추적성 3각 연결의 한 축
    mlflow.log_params({...})                 # seed, 하이퍼파라미터, split 규칙 전부
    mlflow.log_metrics({...})
```

사용 규약(태그 규칙, 반드시 기록할 지표)은
[Wiki - MLflow 접속](https://github.com/fighting-team-tree/autonomous-driving-challenge-2026/wiki)
을 보세요.

## 운영

```bash
docker compose logs -f mlflow      # 로그
docker compose restart mlflow      # 재시작
docker compose pull && docker compose up -d --build   # 업데이트
```

### 백업

Postgres에 모든 run 기록이 들어 있습니다. **대회 막판에 날리면 복구 불가입니다.**

```bash
docker compose exec -T postgres pg_dump -U mlflow mlflow | gzip > mlflow-$(date +%F).sql.gz
```

주 1회, 특히 첫 제출(8/18) 직전에 받아두세요.

## 로컬 스모크 테스트

compose 를 고쳤다면 VM 에 올리기 전에 노트북에서 먼저 돌려보세요.
`compose.test.yml` 이 R2 자리에 MinIO 를 세우고 포트를 8080/8443 으로 옮깁니다.

```bash
cd infra/mlflow

cat > .env <<EOF
POSTGRES_PASSWORD=testpg1234
MLFLOW_FLASK_SERVER_SECRET_KEY=$(openssl rand -hex 32)
R2_ACCESS_KEY_ID=minioadmin
R2_SECRET_ACCESS_KEY=minioadmin123
R2_ENDPOINT=http://minio:9000
R2_BUCKET=mlflow-test
MLFLOW_HOSTNAME=localhost
ACME_EMAIL=test@example.com
EOF
sed -e 's/^admin_username = .*/admin_username = testadmin/' \
    -e 's/^admin_password = .*/admin_password = testpass1234/' \
    basic_auth.ini.example > basic_auth.ini

docker compose -f docker-compose.yml -f compose.test.yml up -d --build

# 인증 없이 → 401,  인증하면 → 200
curl -sk -o /dev/null -w '%{http_code}\n' https://localhost:8443/api/2.0/mlflow/experiments/search
curl -sk -u testadmin:testpass1234 -o /dev/null -w '%{http_code}\n' https://localhost:8443/api/2.0/mlflow/experiments/search

docker compose -f docker-compose.yml -f compose.test.yml down -v
rm -f .env basic_auth.ini
```

## 검증 중 실제로 걸렸던 것들

로컬 검증에서 세 번 막혔습니다. 전부 반영돼 있으니 참고만 하세요.

| 증상 | 원인 | 해결 |
|---|---|---|
| `ImportError: ... requires the Flask-WTF package` 후 crash-loop | `mlflow` 만 설치하면 basic-auth 앱이 안 뜬다 | Dockerfile 에서 `mlflow[auth]` 설치 |
| `A static secret key needs to be set for CSRF protection` | basic-auth 는 Flask 시크릿을 요구한다 | `MLFLOW_FLASK_SERVER_SECRET_KEY` 설정 |
| 모든 API 가 `403 Invalid Host header - possible DNS rebinding attack detected` | MLflow 3.x 는 Host 헤더를 검증하고, **기본 허용은 localhost 와 사설 IP 뿐**이다 | `MLFLOW_SERVER_ALLOWED_HOSTS=${MLFLOW_HOSTNAME}` 설정 |

마지막 항목이 특히 함정입니다. 로컬에서는 `localhost` 라 통과하지만,
공개 호스트명으로 프록시하는 순간 **전부 403** 이 됩니다.

## 한계

- 인증은 **MLflow 내장 basic-auth 한 겹**입니다. 프록시에 basic auth를 겹치면
  클라이언트가 헤더를 하나만 보낼 수 있어 충돌합니다. 더 강하게 가려면
  Cloudflare Tunnel + Access(Google 로그인)로 바꾸는 것이 다음 단계입니다.
  단 Cloudflare에 등록된 도메인이 필요합니다.
- artifact를 서버가 대리 전송하므로 **큰 체크포인트는 VM 대역폭을 거칩니다.**
  무료 티어 VM에서 느리면, 체크포인트만 R2에 직접 올리고 MLflow에는 경로만
  기록하는 방식으로 바꾸세요.
