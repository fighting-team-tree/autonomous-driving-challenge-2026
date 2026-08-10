# 2026 자율주행 AI 챌린지 — Team Tree

가설을 세우고, 실험하고, 배운 것을 남기는 팀 저장소입니다.

📖 **[문서 사이트](https://fighting-team-tree.github.io/autonomous-driving-challenge-2026/)**
· 📝 [Wiki](https://github.com/fighting-team-tree/autonomous-driving-challenge-2026/wiki)
· 🏁 [대회 사이트](https://dxchallenge.ai.kr/)

## 일정

| | |
|---|---|
| 본대회 시작 | 8/10 — 시작됨 |
| **제출 / 리더보드 오픈** | **8/18** |
| 리더보드 마감 | 9/23 |
| 수상자 발표 | 10/14 |

**제출은 트랙당 5회뿐입니다.**

## 트랙

세 트랙 모두 참여. 수상은 최대 2개 분야까지 가능합니다.

| 트랙 | 베이스라인 | 핵심 지표 |
|---|---|---|
| [모션 Planning](https://fighting-team-tree.github.io/autonomous-driving-challenge-2026/competition/planning/) | V-Max + Waymax | 충돌·도로이탈·진행도·승차감 |
| [미래궤적 예측](https://fighting-team-tree.github.io/autonomous-driving-challenge-2026/competition/prediction/) | SMART | minADE₆ + 추론시간 |
| [E2E Driving](https://fighting-team-tree.github.io/autonomous-driving-challenge-2026/competition/e2e/) | VAD-tiny | L2(3초) + 추론시간 |

## 처음 왔다면

1. **[작업 규칙 (`AGENTS.md`)](AGENTS.md)** — Git 컨벤션, 실험 기록법, 커밋 금지 항목
2. **[사전설명회 정리](https://fighting-team-tree.github.io/autonomous-driving-challenge-2026/competition/briefing/)**
   — 가이드라인 PDF에 **없는** 공략 포인트
3. **[실험 기록](https://fighting-team-tree.github.io/autonomous-driving-challenge-2026/experiments/)**
4. Wiki에서 환경 세팅과 데이터 받는 법 확인

## 로컬에서 문서 보기

```bash
pip install -r requirements-docs.txt
mkdocs serve          # http://localhost:8000
```

## ⚠️ 이 저장소는 public입니다

문서에는 **가설과 배운 것**을 씁니다.
seed·정확한 하이퍼파라미터·split 같은 **복붙하면 바로 돌아가는 값은 MLflow에만** 남깁니다.
데이터·체크포인트·시크릿은 커밋하지 않습니다 — 이유와 전체 규칙은 [`AGENTS.md`](AGENTS.md)에 있습니다.

## 라이선스

[MIT](LICENSE)
