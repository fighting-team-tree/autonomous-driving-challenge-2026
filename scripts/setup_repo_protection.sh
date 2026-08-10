#!/usr/bin/env bash
# main 브랜치 보호와 머지 정책을 설정한다. 여러 번 실행해도 안전하다(멱등).
#
#   bash scripts/setup_repo_protection.sh
#
# 설계 원칙: 기계가 판정할 수 있는 것만 강제하고, 사람 판단은 강제하지 않는다.
#   강제함  — PR 없이 main 푸시 불가 / CI 통과 필수 / force push·삭제 불가
#   강제 안 함 — 승인 인원 0명. 4명 6주짜리 대회에서 리뷰 대기는 비용이 크다.
#
# 우리 조건(public 레포 + Free org)에서 브랜치 보호는 사용 가능하지만,
# push ruleset(파일 크기·확장자 차단)은 Team 플랜 + private 전용이라 쓸 수 없다.
# 그 역할은 .github/workflows/guard.yml 이 대신하므로 필수 검사에 포함한다.

set -euo pipefail

REPO="${REPO:-fighting-team-tree/autonomous-driving-challenge-2026}"

# true  = 관리자도 우회 불가. 실수로 main에 직접 푸시하는 것을 진짜로 막는다.
# false = 관리자는 우회 가능. 급할 때 편하지만 "무분별한 main 푸시"는 못 막는다.
# 막히면 이 값을 false로 바꿔 다시 실행하면 즉시 풀린다.
ENFORCE_ADMINS="${ENFORCE_ADMINS:-true}"

echo "▶ 대상: $REPO  (enforce_admins=$ENFORCE_ADMINS)"

echo "▶ 머지 정책: squash 전용 + 머지 후 브랜치 자동 삭제"
gh api -X PATCH "repos/$REPO" \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F allow_auto_merge=true \
  -F delete_branch_on_merge=true \
  -f squash_merge_commit_title=PR_TITLE \
  -f squash_merge_commit_message=PR_BODY \
  --silent

echo "▶ main 브랜치 보호"
gh api -X PUT "repos/$REPO/branches/main/protection" --input - <<JSON --silent
{
  "required_status_checks": {
    "strict": false,
    "contexts": ["build", "guard"]
  },
  "enforce_admins": $ENFORCE_ADMINS,
  "required_pull_request_reviews": {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_linear_history": false,
  "required_conversation_resolution": false,
  "block_creations": false
}
JSON

echo
echo "✅ 완료. 적용된 내용:"
gh api "repos/$REPO/branches/main/protection" --jq '{
  PR_필수: (.required_pull_request_reviews != null),
  필요_승인수: .required_pull_request_reviews.required_approving_review_count,
  필수_검사: .required_status_checks.contexts,
  관리자도_적용: .enforce_admins.enabled,
  force_push_허용: .allow_force_pushes.enabled,
  삭제_허용: .allow_deletions.enabled
}'

cat <<'NOTE'

이제부터 main에 직접 푸시할 수 없습니다. 작업 흐름:

  git switch -c exp/M002-token-slim
  # ... 작업 ...
  git push -u origin exp/M002-token-slim
  gh pr create --fill
  gh pr merge --squash --auto     # CI 통과하는 즉시 자동 머지

되돌리려면:
  gh api -X DELETE repos/OWNER/REPO/branches/main/protection
NOTE
