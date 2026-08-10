# AGENTS.md

2026 자율주행 AI 챌린지 — Team Tree 작업 규칙. **사람과 코딩 에이전트 모두 이 파일을 따른다.**

이 파일이 규칙의 유일한 정본이다. `CLAUDE.md`는 이 파일을 import하고, 문서 사이트의 `docs/conventions.md`는 이 파일을 그대로 렌더한다. 규칙을 바꿀 때는 **여기만** 고친다.

## 이 레포가 무엇인가

모델 학습이 주 목적이고, 이 레포는 **"어떤 가설을 세웠고 무엇을 실험했으며 무엇을 배웠는가"를 팀 4명이 공유하는 곳**이다. 코드 저장소가 아니다.

트랙당 리더보드 제출은 **5회뿐**이다. 무엇이 왜 실패했는지 기록이 남지 않으면 4명이 6주 동안 같은 실패를 반복하고 제출 예산을 태운다. 실험 기록은 편의 기능이 아니라 그걸 막는 장치다.

## 절대 규칙

### 1. 이 레포는 public이다 — 복붙 가능한 설정값을 문서에 쓰지 않는다

`docs/` 마크다운에 쓰는 것: **가설, 설계 의도, 결과 해석, 배운 것.**
`docs/` 마크다운에 쓰지 않는 것: **seed, 정확한 하이퍼파라미터 표, train/val split 규칙, 실행 커맨드 전문.**

후자는 전부 MLflow(비공개 클라우드 VM)에 남긴다. 문서에서는 run URL로 가리킨다.

> 이유: 주최측이 사전설명회에서 작년 사례를 명시적으로 경고했다 — 두 팀이 **train/val split의 시드까지 동일, 학습 파라미터 수치 일치, 주석까지 사실상 동일**해서 문제가 됐고, 본선 4개 팀은 코드 검증을 받는다. 경쟁팀이 165개다.

에이전트 주의: 문서를 "친절하게" 완성하려고 하이퍼파라미터 표를 펼쳐놓는 실수가 잦다. 하지 말 것.

### 2. 데이터·체크포인트·시크릿을 커밋하지 않는다

`.gitignore`에 정의돼 있다. `git add .` 대신 경로를 명시해서 add한다.

GitHub은 100MB 초과 push를 거부하지만 **50MB 체크포인트는 통과하고 레포를 영구 오염시킨다.** 히스토리 정리는 force-push 재작성이 필요해서 4명이 동시 작업 중이면 사실상 불가능하다.

R2 액세스 키와 MLflow VM 주소·인증정보는 `.env`에만 둔다. `.env.example`에는 키 이름만 두고 값은 비운다.

### 3. 실험 문서는 가설을 먼저 쓰고 학습을 돌린다

`배경 → 가설 → 실험 설계`를 **돌리기 전에** 작성한다. 결과를 보고 나서 쓰면 사후 합리화가 되고, 그 순간 이 문서는 실험 로그가 아니라 결과 덤프가 된다.

### 4. 빈 스캐폴딩을 미리 만들지 않는다

`src/` 같은 빈 폴더를 "나중에 쓸 것 같아서" 만들지 않는다. 세 트랙의 베이스라인(V-Max / SMART / VAD)은 각각 별도 저장소를 fork해서 쓰는 구조라, 미리 판 폴더는 안 쓰이거나 규칙만 어긋난다. 실제로 필요할 때 만든다.

## 저장소 구조

```
AGENTS.md / CLAUDE.md      규칙 정본 + Claude용 import
docs/                      → GitHub Pages (MkDocs Material)
  index.md                 팀 홈
  conventions.md           AGENTS.md를 include
  competition/             대회 정보 (가이드라인 PDF + 사전설명회 정리)
  experiments/             실험 기록 — 트랙별 하위 폴더
  decisions.md             팀 결정 기록
scripts/                   MkDocs hook
```

**Wiki는 별도 저장소다.** 역할이 다르다:

| | 담는 것 |
|---|---|
| **Pages** (`docs/`) | 대회 정보, 실험 기록, 결정 기록 — PR을 거치는 영구 지식 |
| **Wiki** | 환경 세팅 삽질, 데이터 받는 법, MLflow 접속법, 트러블슈팅, 회의록 — 브라우저에서 바로 고치는 휘발성 메모 |
| **MLflow** | metric/loss curve, 하이퍼파라미터, seed, split, 체크포인트 |

손으로 지표 표를 채우지 않는다. 숫자는 MLflow가 자동으로 먹는다.

## Git 컨벤션

### 브랜치

```
exp/<EXP-ID>-<slug>      exp/M003-shared-decoder
docs/<slug>              docs/briefing-summary
infra/<slug>             infra/r2-bucket
fix/<slug>               fix/nan-batch-skip
```

### 커밋

Conventional Commits에 `exp` 타입을 추가해서 쓴다. scope는 `planning | prediction | e2e | docs | infra`.

```
exp(prediction): EXP-M003 6-mode 디코더를 공유 헤드로 교체
docs(competition): 사전설명회 공략 포인트 정리
fix(planning): 평가 중 NaN 발생 시 배치 스킵
chore(infra): R2 버킷 동기화 스크립트
```

### 추적성 3각 연결 — 이 컨벤션이 존재하는 이유

수상 후보가 되면 **재현성 평가**에서 *"이 점수를 낸 코드가 정확히 무엇인가"*에 답해야 한다. 아래 셋이 다 걸려야 문서 ↔ 코드 ↔ 지표가 왕복 가능하다:

1. 브랜치명과 커밋 메시지에 `EXP-ID`
2. 학습 코드에서 `mlflow.set_tag("exp_id", "EXP-M003")` — git commit은 MLflow가 자동 기록
3. 실험 문서 frontmatter의 `mlflow:` run URL

하나라도 빠지면 연결이 끊기고, 대회 6주차에 복원은 불가능하다.

### PR — main 직접 푸시는 차단돼 있다

```bash
git switch -c exp/M002-token-slim
# ... 작업 ...
git push -u origin exp/M002-token-slim
gh pr create --fill
gh pr merge --squash --auto      # CI 통과하는 즉시 자동 머지
```

무엇이 강제되고 무엇이 아닌지:

| 강제됨 (기계가 막음) | 강제 안 됨 (사람에게 맡김) |
|---|---|
| PR 없이 main 푸시 불가 | **승인 인원 0명** — 혼자 열고 혼자 머지 가능 |
| CI 통과 필수 (`build` + `guard`) | 리뷰 코멘트 해결 여부 |
| force push · main 삭제 불가 | |

승인을 강제하지 않는 이유: 되돌릴 수 없는 사고(시크릿 유출, 체크포인트가 히스토리에 박힘,
force push로 남의 커밋 증발)는 기계가 막는다. 반면 "이 가설이 타당한가"는 새벽 3시에
블로킹할 가치가 없다. 4명 6주에서 승인 대기는 실제로 비싸다.

`gh pr merge --squash --auto` 를 습관으로 쓰면 CI를 지켜보지 않아도 된다.

리뷰가 필요하면 요청하되, 기다릴지 말지는 본인이 정한다. `.github/CODEOWNERS`에 걸린
파일(규칙·설정·워크플로)은 자동으로 리뷰 요청이 나가지만 **승인 없이도 머지된다.**

브랜치 보호 설정은 `scripts/setup_repo_protection.sh` 에 코드로 남아 있다.

## 실험 기록 작성법

`docs/experiments/_template.md`를 복사해서 `docs/experiments/<track>/EXP-<ID>-<slug>.md`로 만든다.

ID 규칙: Planning은 `P001`, 궤적예측은 `M001`, E2E는 `E001`부터 순번.

frontmatter는 문서 목록 표를 자동 생성하는 데 쓰이므로 필드명을 바꾸지 않는다:

```yaml
---
id: EXP-M003
track: prediction        # planning | prediction | e2e
status: 진행중            # 진행중 | 채택 | 기각 | 보류
hypothesis: 한 줄 요약
result: 한 줄 요약 (상세 수치는 MLflow)
mlflow: <run URL>
author: 이름
date: 2026-08-14
---
```

`docs/experiments/index.md`의 표는 `scripts/gen_experiment_index.py`가 빌드 시 자동 생성한다. **손으로 고치지 않는다.**

## 문서 작성

- 한국어로 쓴다.
- 수식은 `$...$` / `$$...$$` (arithmatex + MathJax 설정돼 있음).
- 그림·HTML 리포트는 `docs/assets/`에 둔다.
- 새 페이지를 추가하면 `mkdocs.yml`의 `nav`에도 넣는다. CI가 `--strict`로 빌드하므로 nav에 없거나 링크가 깨지면 배포가 실패한다.

## 로컬 확인

```bash
pip install -r requirements-docs.txt
mkdocs serve            # http://localhost:8000
python scripts/gen_experiment_index.py   # hook 자체 점검
```
