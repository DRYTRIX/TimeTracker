#!/usr/bin/env bash
# Apply repository rulesets that require the `ci-pass` check.
# Usage: gh auth status && bash scripts/ci/apply-branch-rulesets.sh
#
# Note: rc/** intentionally allows branch deletion so release-finalize can
# remove rc/vX.Y.Z after merge. develop/main block deletion.
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"

create_or_update() {
  local name="$1"
  local payload="$2"
  local existing
  existing=$(gh api "repos/${REPO}/rulesets" --jq ".[] | select(.name==\"${name}\") | .id" | head -1 || true)
  if [ -n "$existing" ]; then
    echo "Updating ruleset '$name' (id=$existing)"
    echo "$payload" | gh api --method PUT "repos/${REPO}/rulesets/${existing}" --input - >/dev/null
  else
    echo "Creating ruleset '$name'"
    echo "$payload" | gh api --method POST "repos/${REPO}/rulesets" --input - >/dev/null
  fi
}

# Remove legacy combined ruleset if present
OLD=$(gh api "repos/${REPO}/rulesets" --jq '.[] | select(.name=="CI gate (develop and rc)") | .id' || true)
if [ -n "${OLD:-}" ]; then
  gh api -X DELETE "repos/${REPO}/rulesets/${OLD}" >/dev/null || true
fi

create_or_update "CI gate (develop)" "$(cat <<'JSON'
{
  "name": "CI gate (develop)",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {"include": ["refs/heads/develop"], "exclude": []}
  },
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": true,
        "required_status_checks": [{"context": "ci-pass"}]
      }
    }
  ],
  "bypass_actors": []
}
JSON
)"

create_or_update "CI gate (rc)" "$(cat <<'JSON'
{
  "name": "CI gate (rc)",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {"include": ["refs/heads/rc/**"], "exclude": []}
  },
  "rules": [
    {"type": "non_fast_forward"},
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": true,
        "required_status_checks": [{"context": "ci-pass"}]
      }
    }
  ],
  "bypass_actors": []
}
JSON
)"

create_or_update "CI gate (main)" "$(cat <<'JSON'
{
  "name": "CI gate (main)",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {"include": ["refs/heads/main"], "exclude": []}
  },
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "do_not_enforce_on_create": true,
        "required_status_checks": [{"context": "ci-pass"}]
      }
    }
  ],
  "bypass_actors": []
}
JSON
)"

echo "✅ Rulesets applied on $REPO"
