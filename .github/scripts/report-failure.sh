#!/usr/bin/env bash
# Open (or comment on) a GitHub issue when a scheduled job fails, @mentioning
# the commissioner so GitHub emails him. One open issue per workflow, so a job
# that keeps failing adds comments instead of new issues.
set -euo pipefail
title="⚠️ ${WORKFLOW} failed"
run_url="${RUN_URL:-${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}}"
existing=$(gh issue list --repo "$GITHUB_REPOSITORY" --state open --search "in:title \"${WORKFLOW} failed\"" \
  --json number,title --jq "map(select(.title == \"$title\")) | .[0].number // empty")
if [ -n "$existing" ]; then
  gh issue comment "$existing" --repo "$GITHUB_REPOSITORY" --body "Failed again: $run_url"
else
  gh issue create --repo "$GITHUB_REPOSITORY" --title "$title" --body "@danigle the **${WORKFLOW}** job failed.

Run log: $run_url

Close this issue once it's fixed; the next failure opens a new one."
fi
