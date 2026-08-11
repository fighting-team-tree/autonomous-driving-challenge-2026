---
id: EXP-P001
track: planning
status: 진행중
hypothesis: 배포된 제출 예제 2개를 우리 환경의 평가기에 넣으면 등속≈60점 / SAC≈80점이 재현되고, 평가가 30분 제한 안에 끝난다
result: ""
mlflow: ""
author: TBD
date: 2026-08-12
---

# EXP-P001 — 환경과 제출 경로가 뚫리는가

## 배경

Planning 트랙에는 **모델 성능 이전에 통과해야 할 하드 게이트가 두 개** 있습니다.

1. **CUDA 13 휠 → NVIDIA 드라이버 ≥ 580.** 우리 GPU는 3060/5060이고 Colab/Runpod는
   인스턴스마다 드라이버가 다릅니다. 여기서 막히면 학습을 시작조차 못 합니다.
2. **제출물이 JAX-traceable해야 합니다.** 평가기가 `jit(vmap(...))` 안에서 actor를
   호출합니다. 게다가 평가 환경의 `jax`/`flax`/`numpy`가 `==` 고정이라, 충돌하는
   `requirements.txt`는 설치 단계에서 거부됩니다.

**제출은 트랙당 5회뿐입니다.** 그중 하나를 "실행이 안 돼서 0점"으로 날리는 것이 가장
아까운 손실입니다. 실제로 배포된 평가 코드는 제출물이 예외를 던지면 그 batch 전체를
0점 처리합니다.

그래서 첫 실험의 목적은 점수를 올리는 게 아니라 **파이프라인을 신뢰할 수 있는지
확인하고, 이후 모든 실험의 기준선과 시간 예산을 확보하는 것**입니다.

관련: [Planning 트랙 문서](../../competition/planning.md),
[결정 기록 D-011](../../decisions.md)

## 가설

배포된 두 제출 예제를 우리 환경의 평가기에 그대로 넣으면:

1. `submission_example_const_vel` 이 **총점 60점 근처**를 낸다
   (설명회에서 등속 모델 기준선으로 제시한 값)
2. `submission_example_vmax_sac` 이 **총점 80점 근처**를 낸다
   (설명회에서 배포 SAC 예제 기준선으로 제시한 값)
3. 전체 평가가 **30분 제한 안에** 끝난다
4. `uv sync` 가 우리 드라이버에서 성공한다

넷 중 하나라도 어긋나면 우리 환경이 주최측과 다르다는 뜻이고, 그 차이를 먼저 없애야
이후 실험 결과를 믿을 수 있습니다.

## 실험 설계

- **바꾼 것**: 없음. 배포된 예제 그대로
- **고정한 것**: 예제 코드, 평가 스크립트, `BATCH_SIZE` 기본값(64)
- **비교 대상**: 설명회에서 제시된 기준선 (등속 ≈60, SAC ≈80, 사람 ≈1.0)
- **판정 기준**
    - 두 예제 점수가 기준선 ±5점 이내 → **채택** (파이프라인 신뢰 가능)
    - 벗어나면 → **보류**. 원인을 찾을 때까지 다른 실험을 시작하지 않는다

### 절차

```bash
# 0) 드라이버 확인 — 팀원 전원 / 사용할 모든 인스턴스에서
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv

# 1) 두 저장소 준비
git clone https://github.com/jaehyuck0103/V-Max
git clone https://github.com/jaehyuck0103/dxchallenge_planning_eval_open
cd dxchallenge_planning_eval_open && uv sync

# 2) 작은 데이터셋으로 평가 (livinglab 9개가 가장 작음)
CUDA_VISIBLE_DEVICES=0 uv run evaluate.py \
    --path_dataset <val>.tfrecord@N \
    --submission submission_example_const_vel

CUDA_VISIBLE_DEVICES=0 uv run evaluate.py \
    --path_dataset <val>.tfrecord@N \
    --submission submission_example_vmax_sac
```

결과는 `results/<제출물 이름>/evaluation_episodes.csv`(시나리오별)와
`evaluation_results.txt`(평균)에 남습니다.

### 반드시 측정할 것

이 값들이 이후 모든 Planning 실험의 예산이 됩니다.

| 측정 | 왜 필요한가 |
|---|---|
| 팀원별·인스턴스별 **드라이버 버전** | 580 미만이면 그 환경은 Planning에 못 씀 |
| `uv sync` 성공 여부와 소요 시간 | 실패 시 대안 환경을 찾아야 함 |
| 두 예제의 **총점** | 이후 실험의 baseline |
| 시나리오 수 대비 **평가 소요 시간** | 5만 시나리오 / 30분 환산 |
| 우리 GPU와 **RTX 4090의 배율** | 주최측 기준(베이스라인 5분30초)과 비교 |
| `BATCH_SIZE` 를 낮춰야 했는가 | 3060 12GB에서 64가 OOM인지 |
| `progress / comfort / overlap / offroad` 개별 값 | 어디서 점수를 잃는지 |

마지막 항목이 중요합니다. 총점만 보면 다음에 무엇을 고쳐야 할지 알 수 없습니다.

!!! warning "여기에 seed·하이퍼파라미터를 적지 마세요"
    이 저장소는 public입니다. 복붙하면 바로 돌아가는 값은 MLflow에만 남깁니다.

## 결과

<!-- 실제로 돌린 사람이 채웁니다. 상세 수치는 MLflow. -->

| 항목 | 기대값 | 측정값 |
|---|---|---|
| 드라이버 버전 | ≥ 580 | |
| `submission_example_const_vel` 총점 | ≈ 60 | |
| `submission_example_vmax_sac` 총점 | ≈ 80 | |
| 평가 소요 시간 (시나리오 N개) | — | |
| 5만 시나리오 환산 | < 30분 | |
| RTX 4090 대비 배율 | — | |
| `BATCH_SIZE` | 64 | |

## 판정 & 배운 것

<!-- 채택 / 기각 / 보류 와 그 이유 -->

## 다음

- **EXP-P002** — SAC 예제의 손실에 **comfort 를 추가**. 배포 예제는 승차감이
  손실에서 빠져 있는데 배점은 30%다
- **EXP-P003** — **goal 조건화**. `log_trajectory` 는 전부 소거되지만 ego의 마지막
  logged 위치(x, y)만 goal 로 남는다 (`get_goal_xy`). 이걸 안 쓰면 손해다
- 시간 여유가 5.5배로 확인되면, 경량화가 아니라 **정확도 쪽에 예산을 쓰는 방향**으로
  간다 (궤적예측 트랙과 정반대)
