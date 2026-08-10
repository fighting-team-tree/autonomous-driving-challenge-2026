"""docs/experiments/**/*.md 의 frontmatter를 읽어 실험 목록 표를 생성한다.

`docs/experiments/index.md` 안의 <!-- EXPERIMENT_INDEX --> 자리에 표를 주입한다.

MkDocs 1.4+ 의 네이티브 `hooks:` 기능이라 플러그인 설치도 별도 CI 스텝도 필요 없고,
`mkdocs serve` 로컬 미리보기에서도 그대로 동작한다.

손으로 관리하는 인덱스는 실험 15개쯤에서 반드시 죽는다. 이 파일이 그 규율을 대체한다.

자체 점검:  python scripts/gen_experiment_index.py
"""

from pathlib import Path

import yaml  # mkdocs가 이미 의존하므로 추가 설치 불필요

MARKER = "<!-- EXPERIMENT_INDEX -->"

TRACK_LABEL = {"planning": "Planning", "prediction": "궤적예측", "e2e": "E2E"}
STATUS_ICON = {"채택": "✅", "기각": "❌", "진행중": "🔄", "보류": "⏸️"}

EMPTY_MESSAGE = (
    "!!! info \"아직 기록된 실험이 없습니다\"\n"
    "    `_template.md`를 복사해서 "
    "`experiments/<track>/EXP-<ID>-<slug>.md`로 만드세요."
)


def _read_frontmatter(path: Path) -> dict | None:
    """파일 앞머리의 YAML frontmatter를 파싱한다. 없거나 id가 없으면 None."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None
    return meta if isinstance(meta, dict) and meta.get("id") else None


def _build_table(experiments_dir: Path) -> str:
    if not experiments_dir.is_dir():
        return EMPTY_MESSAGE

    rows = []
    for path in sorted(experiments_dir.rglob("*.md")):
        # 템플릿(_로 시작)과 인덱스 자신은 제외
        if path.name.startswith("_") or path.name == "index.md":
            continue
        meta = _read_frontmatter(path)
        if meta is None:
            continue

        href = path.relative_to(experiments_dir).as_posix()
        status = str(meta.get("status", ""))
        track = str(meta.get("track", ""))
        mlflow_url = meta.get("mlflow")
        rows.append(
            "| [{id}]({href}) | {track} | {icon} {status} | {hypothesis} "
            "| {result} | {mlflow} | {date} |".format(
                id=meta["id"],
                href=href,
                track=TRACK_LABEL.get(track, track),
                icon=STATUS_ICON.get(status, ""),
                status=status,
                hypothesis=meta.get("hypothesis", ""),
                result=meta.get("result") or "—",
                mlflow=f"[run]({mlflow_url})" if mlflow_url else "—",
                date=meta.get("date", ""),
            )
        )

    if not rows:
        return EMPTY_MESSAGE

    header = (
        "| ID | 트랙 | 상태 | 가설 | 결과 | MLflow | 날짜 |\n"
        "|---|---|---|---|---|---|---|"
    )
    return "\n".join([header, *rows])


def on_page_markdown(markdown: str, page=None, config=None, **kwargs) -> str:
    """MkDocs 이벤트 훅. MARKER가 있는 페이지에서만 동작한다."""
    if MARKER not in markdown:
        return markdown
    docs_dir = Path(config["docs_dir"])
    return markdown.replace(MARKER, _build_table(docs_dir / "experiments"))


if __name__ == "__main__":
    import tempfile
    import textwrap

    def _write(path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(body), encoding="utf-8")

    with tempfile.TemporaryDirectory() as tmp:
        docs = Path(tmp)
        _write(
            docs / "experiments" / "prediction" / "EXP-M001-flops.md",
            """\
            ---
            id: EXP-M001
            track: prediction
            status: 채택
            hypothesis: 디코더 공유로 FLOPs 감소
            result: minADE6 1.42
            mlflow: http://example.test/run/1
            date: 2026-08-14
            ---
            본문
            """,
        )
        # 템플릿은 표에서 빠져야 한다
        _write(docs / "experiments" / "_template.md", "---\nid: EXP-XXX\n---\n")
        # frontmatter 없는 파일은 무시돼야 한다
        _write(docs / "experiments" / "notes.md", "frontmatter 없음\n")

        out = on_page_markdown(MARKER, config={"docs_dir": str(docs)})
        assert "EXP-M001" in out, out
        assert "prediction/EXP-M001-flops.md" in out, "링크 경로가 잘못됨"
        assert "궤적예측" in out, "트랙 라벨 미적용"
        assert "✅" in out, "상태 아이콘 미적용"
        assert "EXP-XXX" not in out, "템플릿이 표에 섞였다"
        assert out.count("\n") == 2, f"행 수가 틀림:\n{out}"

        # 마커가 없는 페이지는 건드리지 않는다
        assert on_page_markdown("본문만", config={"docs_dir": str(docs)}) == "본문만"

    with tempfile.TemporaryDirectory() as empty:
        out = on_page_markdown(MARKER, config={"docs_dir": empty})
        assert "아직 기록된 실험이 없습니다" in out, out

    print("ok — gen_experiment_index 자체 점검 통과")
