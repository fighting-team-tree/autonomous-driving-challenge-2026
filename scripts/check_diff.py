"""PR diff에 들어오면 안 되는 파일이 있는지 검사한다.

GitHub의 push ruleset("restrict file size / file extensions")은 **GitHub Team 플랜 +
private 레포 전용**이라 우리(Free 플랜 + public 레포)는 쓸 수 없다. 그래서 CI가 그
역할을 대신한다.

`.gitignore`와 역할이 다르다:
  - .gitignore = 실수로 `git add` 되는 것을 막는 **규약**
  - 이 스크립트 = 규약을 우회했을 때(`git add -f`, .gitignore 추가 이전 커밋,
    다른 머신에서 온 브랜치) 잡는 **집행**

50MB 체크포인트는 GitHub의 100MB 제한을 통과하고 히스토리에 영구히 박힌다.
지우려면 force-push 재작성이 필요한데, 4명이 동시에 작업 중이면 사실상 불가능하다.

사용:
    python3 scripts/check_diff.py <base_sha> <head_sha>
    python3 scripts/check_diff.py --self-test
"""

from __future__ import annotations

import fnmatch
import subprocess
import sys
from pathlib import PurePosixPath

MAX_BYTES = 5 * 1024 * 1024  # 5MB. 문서용 이미지는 한참 아래여야 정상

# 가중치/데이터 계열 — 레포에 들어오면 안 된다
BLOCKED_SUFFIXES = {
    ".pth", ".pt", ".ckpt", ".safetensors", ".onnx", ".engine", ".h5",
    ".tfrecord", ".pkl", ".pickle", ".npz", ".npy", ".parquet",
}

# 시크릿 계열 — public 레포다
BLOCKED_PATTERNS = [
    ".env", ".env.*",
    "*.pem", "*.key",
    "credentials*",
    "service-account*.json",
]

ALLOWED_EXCEPTIONS = {".env.example"}


def violations(path: str, size: int) -> list[str]:
    """파일 하나에 대한 위반 사유 목록. 빈 리스트면 통과."""
    name = PurePosixPath(path).name
    found = []

    if name in ALLOWED_EXCEPTIONS:
        return found

    if PurePosixPath(path).suffix.lower() in BLOCKED_SUFFIXES:
        found.append("데이터/가중치 파일 확장자")

    if any(fnmatch.fnmatch(name, pat) for pat in BLOCKED_PATTERNS):
        found.append("시크릿으로 보이는 파일명")

    if size > MAX_BYTES:
        found.append(f"파일 크기 {size / 1024 / 1024:.1f}MB > {MAX_BYTES // 1024 // 1024}MB")

    return found


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout


def _changed_files(base: str, head: str) -> list[str]:
    """추가·수정·복사·이름변경된 파일 경로. 삭제는 검사할 필요가 없다."""
    out = _git("diff", "--name-only", "--diff-filter=ACMR", f"{base}...{head}")
    return [line for line in out.splitlines() if line.strip()]


def _size_at(rev: str, path: str) -> int:
    try:
        return int(_git("cat-file", "-s", f"{rev}:{path}").strip())
    except subprocess.CalledProcessError:
        return 0  # 해당 리비전에 없으면 검사 대상 아님


def main(base: str, head: str) -> int:
    failures: list[tuple[str, list[str]]] = []

    for path in _changed_files(base, head):
        reasons = violations(path, _size_at(head, path))
        if reasons:
            failures.append((path, reasons))

    if not failures:
        print("✅ 반입 금지 파일 없음")
        return 0

    print("❌ 레포에 들어오면 안 되는 파일이 있습니다:\n")
    for path, reasons in failures:
        print(f"  {path}")
        for reason in reasons:
            print(f"      → {reason}")
    print(
        "\n대처:\n"
        "  1. git rm --cached <파일>  로 추적에서 제외\n"
        "  2. .gitignore 에 패턴이 있는지 확인\n"
        "  3. 데이터·체크포인트는 R2로, 지표는 MLflow로 보낼 것\n"
        "  규칙 전문: AGENTS.md"
    )
    return 1


def _self_test() -> None:
    kb = 1024
    assert violations("docs/assets/diagram.png", 200 * kb) == []
    assert violations(".env.example", 1 * kb) == []
    assert violations("scripts/train.py", 10 * kb) == []
    assert violations("README.md", 4 * kb) == []

    assert "데이터/가중치 파일 확장자" in violations("model.pth", 1 * kb)
    assert "데이터/가중치 파일 확장자" in violations("a/b/scene.PKL", 1 * kb)
    assert "시크릿으로 보이는 파일명" in violations(".env", 1)
    assert "시크릿으로 보이는 파일명" in violations("deploy/.env.production", 1)
    assert "시크릿으로 보이는 파일명" in violations("keys/r2.pem", 1)
    assert "시크릿으로 보이는 파일명" in violations("service-account-prod.json", 1)

    big = violations("docs/assets/huge.png", 9 * kb * kb)
    assert len(big) == 1 and big[0].startswith("파일 크기"), big

    # 확장자와 크기를 동시에 위반하면 둘 다 보고한다
    assert len(violations("run.ckpt", 9 * kb * kb)) == 2

    print("ok — check_diff 자체 점검 통과")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        _self_test()
    elif len(sys.argv) == 3:
        sys.exit(main(sys.argv[1], sys.argv[2]))
    else:
        print(__doc__)
        sys.exit(2)
