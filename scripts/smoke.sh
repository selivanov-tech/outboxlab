#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: smoke.sh readonly|full <api-base-url>

Credentials, one of:
  SMOKE_API_KEY          workspace API key, sent as "Authorization: Bearer"
  SMOKE_WORKSPACE_ID     workspace id, sent as X-Workspace-Id (non-production only)

full mode also needs:
  SMOKE_LEAD_EMAIL       an address you control; it receives a real email
  SMOKE_TIMEOUT_SECONDS  wait for each lead state, default 600
USAGE
}

MODE=${1:-}
BASE_URL=${2:-}
[[ $MODE == readonly || $MODE == full ]] && [[ -n $BASE_URL ]] || { usage; exit 2; }
BASE_URL=${BASE_URL%/}
TIMEOUT_SECONDS=${SMOKE_TIMEOUT_SECONDS:-600}

if [[ -n ${SMOKE_API_KEY:-} ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${SMOKE_API_KEY}")
elif [[ -n ${SMOKE_WORKSPACE_ID:-} ]]; then
  AUTH_HEADER=(-H "X-Workspace-Id: ${SMOKE_WORKSPACE_ID}")
else
  echo "FAIL: set SMOKE_API_KEY or SMOKE_WORKSPACE_ID" >&2
  exit 2
fi

RESPONSE_BODY=""

pass() { echo "  ok   $*"; }
fail() { echo "  FAIL $*" >&2; exit 1; }

request() {
  local method=$1 path=$2 body=${3:-}
  local args=(-sS -X "$method" -H "Accept: application/json" "${AUTH_HEADER[@]}")
  if [[ -n $body ]]; then
    args+=(-H "Content-Type: application/json" --data "$body")
  fi
  local response status
  response=$(curl "${args[@]}" -w $'\n%{http_code}' "$BASE_URL$path") || fail "$method $path: connection failed"
  status=${response##*$'\n'}
  RESPONSE_BODY=${response%$'\n'*}
  [[ $status == 2* ]] || fail "$method $path returned $status: $RESPONSE_BODY"
}

field() {
  python3 -c '
import json, sys
value = json.loads(sys.argv[1])
for key in filter(None, sys.argv[2].split(".")):
    value = value[int(key)] if isinstance(value, list) else value[key]
print("" if value is None else value)
' "$RESPONSE_BODY" "$1"
}

wait_for_lead_state() {
  local campaign_id=$1 expected=$2 deadline=$((SECONDS + TIMEOUT_SECONDS)) state=""
  while (( SECONDS < deadline )); do
    request GET "/campaigns/$campaign_id"
    state=$(field leads.0.state)
    if [[ " $expected " == *" $state "* ]]; then
      return 0
    fi
    [[ $state == failed ]] && fail "lead failed: $(field leads.0.stop_reason)"
    sleep 5
  done
  fail "lead is still '$state' after ${TIMEOUT_SECONDS}s (expected: $expected)"
}

echo "Smoke test ($MODE) against $BASE_URL"

request GET /health
[[ $(field status) == ok ]] || fail "/health: $RESPONSE_BODY"
pass "/health"

request GET /version
pass "/version git_sha=$(field git_sha) app_env=$(field app_env)"

request GET /debug/state
[[ $(field db) == ok ]] || fail "/debug/state: $RESPONSE_BODY"
cursor=$(field mailbox_last_sync_cursor)
if [[ -n $cursor ]]; then
  pass "/debug/state db ok, mailbox sync cursor $cursor"
else
  echo "  warn /debug/state: no mailbox sync cursor yet (seed the mailbox and let the worker poll once)"
fi

request GET /campaigns
pass "/campaigns"

if [[ $MODE == readonly ]]; then
  echo "PASS (read-only)"
  exit 0
fi

[[ -n ${SMOKE_LEAD_EMAIL:-} ]] || fail "full mode needs SMOKE_LEAD_EMAIL"
[[ -n $cursor ]] || fail "full mode needs a mailbox sync cursor first"

request POST /campaigns '{"name":"Smoke test","steps":[{"subject":"OutboxLab smoke test","body":"Please reply to this email, for example: yes, interested.","delay_seconds":0},{"subject":"Re: OutboxLab smoke test","body":"Follow-up that must never be sent once you reply.","delay_seconds":600}]}'
campaign_id=$(field id)
pass "campaign $campaign_id created"

request POST "/campaigns/$campaign_id/leads" "{\"emails\":[\"$SMOKE_LEAD_EMAIL\"]}"
pass "lead added"

request POST "/campaigns/$campaign_id/start"
pass "campaign started, scheduled $(field scheduled)"

wait_for_lead_state "$campaign_id" "sent"
pass "step 1 sent; next send at $(field leads.0.next_send_at)"

echo "  >>   Reply to the email in $SMOKE_LEAD_EMAIL now. Waiting up to ${TIMEOUT_SECONDS}s."
wait_for_lead_state "$campaign_id" "paused"
[[ -z $(field leads.0.next_send_at) ]] || fail "lead paused but a send is still scheduled"
pass "lead paused (intent $(field leads.0.reply_intent)); no send scheduled"

echo "PASS (full)"
