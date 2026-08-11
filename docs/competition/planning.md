# 트랙 1 — 모션 Planning

인지된 주행 환경에서 충돌을 피하고, 도로를 벗어나지 않으며, 목적지 방향으로 진행하는
**미래 궤적을 생성하는** 모델을 만듭니다.

담당: ETRI 노진홍 선임 (jinhong.p.noh@etri.re.kr)

!!! warning "가이드라인 PDF보다 배포된 코드가 정확합니다"
    데이터 지역·날짜, 컷오프 기준, 베이스라인 저장소가 PDF와 다릅니다.
    아래 내용은 **실제 배포된 베이스라인·평가 코드**를 읽고 정리한 것입니다.

## 🔴 먼저 알아야 할 세 가지

### 1. 제출물은 JAX-traceable해야 합니다

평가기가 actor를 `jit(vmap(...))` 안에서 호출합니다. `init`/`select_action`이
JAX tracer(값 없이 shape/dtype만 있는 추상 입력)로 녹화 가능해야 합니다.

**PyTorch 모델을 그대로 제출할 수 없습니다.** 트랙 선택 시 가장 먼저 고려할 제약입니다.

### 2. 평가 환경의 핵심 패키지는 버전이 못 박혀 있습니다

```
jax(CUDA)==0.11.0   flax==0.12.8   numpy==2.5.1   tensorflow-cpu==2.21.0
waymax(고정 rev) + optax, chex 등
```

`jax` 스택·`flax`·`numpy`는 `==` 고정된 **직접 의존성**이라, 다른 버전을 요구하는
`requirements.txt`는 **설치 단계에서 해석 실패로 거부**됩니다.

### 3. CUDA 13 휠 → NVIDIA 드라이버 ≥ 580 필요

베이스라인이 CUDA 13 런타임 휠을 씁니다. 시스템 CUDA 설치는 불필요하지만
**드라이버 버전이 걸립니다.** 로컬 GPU와 Colab/Runpod 드라이버를 먼저 확인하세요 —
여기서 막히면 아무것도 진행되지 않습니다.

## 저장소

| 용도 | 저장소 |
|---|---|
| 학습 베이스라인 | [`jaehyuck0103/V-Max`](https://github.com/jaehyuck0103/V-Max) — valeoai/V-Max의 챌린지 대응 fork |
| **평가 코드** | [`jaehyuck0103/dxchallenge_planning_eval_open`](https://github.com/jaehyuck0103/dxchallenge_planning_eval_open) — 순수 Waymax, V-Max 비의존 |

평가 저장소에 제출 예제 두 개가 들어 있습니다:

- `submission_example_const_vel/` — 등속 주행 planner (goal 추출 예시 `get_goal_xy` 포함)
- `submission_example_vmax_sac/` — V-Max SAC 베이스라인

## 데이터

`<root>/<site>/<date>/*.tfrecord` 구조. 지역은 **hanam · jeju · livinglab** 입니다.

| 지역 | 아카이브 수 | 기간 |
|---|---|---|
| hanam | 31 | 2025-08 ~ 2026-02 |
| jeju | 14 | 2025-02 ~ 2025-04 |
| livinglab | 9 | 2026-03 ~ 2026-04 |

원본은 **301-step** TFRecord (과거 150 / 현재 1 / 미래 150 @ 10Hz).
[궤적예측 트랙](prediction.md)과 동일한 데이터셋입니다.

### 전처리 2단계

```bash
# 1) 301-step → 91-step 윈도우 3개 (시작 step 0 / 100 / 200), WOMD tf_example로 재포장
uv run python scripts/make_91f.py /data/rideflux_301f /data/rideflux_91f

# 2) Waymax 샤드 레이아웃으로 심볼릭 링크 + manifest.csv 생성
uv run python scripts/make_waymax_shards.py /data/rideflux_91f /data/splits/rideflux_trainset_91f
# 마지막 줄에 나오는 경로가 path_dataset 값이다:
#   waymax path: /data/splits/rideflux_trainset_91f/rideflux_trainset_91f.tfrecord@85126
```

학습셋은 **85,126 윈도우**로 나옵니다. `make_91f.py`는 파일 단위 원자적·재개 가능하며,
인자 끝에 숫자를 붙이면(`... <in> <out> 30`) 30개만 처리하는 스모크 런이 됩니다.

## 시뮬레이션 구성

- `PlanningAgentEnvironment` — ego(SDC)만 참가자 planner가 제어. 나머지 객체는
  logged trajectory 재생 (non-reactive)
- ego dynamics: `InvertibleBicycleModel(normalize_actions=True)`
- 에피소드: 9초(91 step) 중 **warmup 11 step 후 80 step 전체 시뮬레이션**

### 참가자에게 주어지는 입력

매 step `waymax.datatypes.SimulatorState`를 받되:

- `log_trajectory`는 **전체 invalid 처리 + 값 0으로 소거**
- **예외: ego의 마지막 logged 위치 (x, y)는 goal로 남습니다** ← 추출 예시는
  `submission_example_const_vel/actor.py`의 `get_goal_xy`
- 관측은 `sim_trajectory`로 — warmup 히스토리(step 0~10)와 지금까지의 rollout.
  비-ego 객체는 logged 궤적 재생. 현재 timestep 이후는 invalid
- `log_traffic_light`는 현재 timestep까지 가시
- **observation 정의와 feature extraction은 전적으로 참가자 몫**

## 평가

### 시간 제한 — PDF의 "PDM 1.5배"가 아닙니다

> 제출물 로딩·jit 컴파일 포함 전체 평가가 **`--time_limit` 기본 1800초(30분)** 안에
> 끝나지 않으면 실패 처리 (`TIME LIMIT EXCEEDED`, 결과 파일 없음)

- testset 약 **5만 시나리오**
- 베이스라인 모델 **5분 30초 @ RTX4090** → 여유 약 5.5배
- 채점 GPU: **RTX ???? 1장 (TBA)**

### 점수식

$$
\text{rideflux score} = \frac{7 \cdot \mathrm{clip}(\text{progress ratio},0,1) + 3 \cdot \text{comfort}}{10} \times (1-\text{overlap}) \times (1-\text{offroad})
$$

| metric | 에피소드 집계 |
|---|---|
| `progress_ratio` | **마지막 step 값** (logged 경로 대비 진행률) |
| `comfort` | **step 평균** (nuPlan 6개 임계값 만족 비율) |
| `overlap` | **max** (충돌 여부 0/1) |
| `offroad_in_box` | **max** (도로이탈 여부 0/1) |

최종 점수는 전체 시나리오 평균. **충돌이나 도로이탈이 한 번이라도 발생하면 그 시나리오는
곱셈 게이트로 0점**입니다.

!!! danger "0점 처리 조건"
    - 참가자 코드가 예외를 던진 시나리오 → 0점 (`error` 컬럼 표시)
    - **batch 안에서 예외 발생 시 그 batch 전체가 0점**
    - 30분 제한 초과 → 전체 실패

## 제출

디렉터리 하나. 필수 파일은 `actor.py`:

```python
def create_actor(submission_dir: str) -> waymax.agents.actor_core.WaymaxActorCore:
    ...
```

- `WaymaxActorCore` 상속 또는 `actor_core_factory` 사용
- weight 파일은 같은 디렉터리에 두고 `submission_dir` 기준으로 로드
- (선택) 모듈 상수 **`BATCH_SIZE = N`** 선언 시 그 batch 크기로 평가 (기본 64).
  너무 크면 OOM으로 제출 실패, 너무 작으면 30분 제한에 걸립니다
- 순수 파이썬 패키지는 제출 디렉터리에 폴더째 넣어도 import 됩니다
  (제출 디렉터리가 `sys.path` 앞에 추가됨)

### action 형식

`select_action(params=None, state, actor_state, rng)` 이 반환하는 `WaymaxActorOutput.action`:

- `data`: float32 `(2,)` = **(가속도, 조향)**, 각각 `[-1, 1]`
  (내부적으로 ±6.0 m/s², ±0.3 curvature로 스케일)
- 범위 밖 값(±inf 포함)은 clip, **NaN 성분은 0.0으로 치환**
- `valid`: bool `(1,)`

### 제출 전 셀프 체크 — 반드시 하세요

평가 저장소에서 주최측과 동일한 환경을 미리 확인할 수 있습니다.

```bash
uv sync                                    # 기본 평가 환경
uv add -r <제출 디렉토리>/requirements.txt   # 충돌하면 여기서 거부됨
```

제출 5회 중 하나를 환경 충돌로 날리는 것이 가장 아까운 손실입니다.

## 학습 · 평가 명령

```bash
# 학습
CUDA_VISIBLE_DEVICES=0 uv run vmax/scripts/training/train.py \
    algorithm=sac network/encoder=lq total_timesteps=25_000_000 \
    algorithm.learning_rate=1e-4 algorithm.buffer_size=1_000_000 \
    algorithm.learning_start=50_000 \
    'algorithm.network.policy.layer_sizes=[256,64,32]' \
    'algorithm.network.value.layer_sizes=[256,64,32]' \
    observation_config.objects.num_closest_objects=16 \
    waymo_dataset=true \
    path_dataset=/data/splits/rideflux_trainset_91f/rideflux_trainset_91f.tfrecord@85126 \
    name_run=abcdef
```

`waymo_dataset=true`가 **필수**입니다 (raw WOMD tf_example, 사전계산된 SDC path 없음).
체크포인트와 TensorBoard 로그는 `runs/<run_name>/`에 쌓입니다.

```bash
# 제출용 policy 가중치 추출 — 체크포인트는 policy+value 전체라 그대로 못 냅니다
uv run python scripts/export_policy_weights.py \
    runs/<run_name>/model/model_final.pkl <submission_dir>/weights.pkl
```

## 이 트랙의 초기 가설 후보

> 실제 실험은 [실험 기록](../experiments/index.md)에 `EXP-P00N` 으로 등록하세요.

- 배포 SAC 예제는 **손실에 승차감(comfort)이 빠져 있습니다** → 배점 30% 구간.
  comfort를 보상에 추가하면 개선 여지
- 충돌·도로이탈이 **곱셈 게이트**이므로, 진행도를 조금 포기하고 안전을 확보하는 쪽이
  기대점수가 높을 가능성
- **goal(ego 마지막 logged 위치)을 명시적으로 조건화**했는가? 안 쓰면 손해
- 시간 여유가 5.5배 → **정확도 쪽에 예산을 더 써도 됩니다.** `BATCH_SIZE` 튜닝으로
  OOM과 시간 제한 사이 최적점 찾기
- 지역별(hanam·jeju·livinglab) 주행 특성 차이 → 지역 조건부 학습 또는 지역별 성능 분석
