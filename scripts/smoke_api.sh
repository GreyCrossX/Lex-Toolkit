#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE_URL:-http://localhost:8000}"
TEST_EMAIL="${TEST_EMAIL:-smoke_user@lex.com}"
TEST_PASSWORD="${TEST_PASSWORD:-smokepass123}"
COOKIE_JAR="$(mktemp)"

cleanup() {
  rm -f "${COOKIE_JAR}"
}
trap cleanup EXIT

format_json() {
  if command -v jq >/dev/null 2>&1; then
    jq .
  else
    python3 -m json.tool 2>/dev/null || cat
  fi
}

extract_access() {
  python3 -c 'import json,sys; data=sys.stdin.read(); 
if not data.strip(): 
    sys.exit(1)
print(json.loads(data).get("access_token",""))'
}

echo "Hitting ${API_BASE}"

echo "1) /health"
curl -fsS "${API_BASE}/health" | format_json

echo "1b) /auth/health"
curl -fsS "${API_BASE}/auth/health" | format_json

echo "2) login (or register fallback)"
login_resp=$(curl -sS -i -c "${COOKIE_JAR}" -X POST "${API_BASE}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASSWORD}\"}")

login_status=$(printf '%s\n' "${login_resp}" | awk 'NR==1{print $2}')
if [[ "${login_status}" == "401" || "${login_status}" == "404" ]]; then
  echo "Login failed (${login_status}); attempting register..."
  reg_resp=$(curl -sS -i -c "${COOKIE_JAR}" -X POST "${API_BASE}/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASSWORD}\",\"role\":\"user\"}")
  reg_status=$(printf '%s\n' "${reg_resp}" | awk 'NR==1{print $2}')
  if [[ "${reg_status}" != "201" ]]; then
    echo "Register failed (status ${reg_status})"
    printf '%s\n' "${reg_resp}"
    exit 1
  fi
  access_token=$(printf '%s\n' "${reg_resp}" | sed -n '/^{/,$p' | extract_access)
else
  access_token=$(printf '%s\n' "${login_resp}" | sed -n '/^{/,$p' | extract_access)
fi

if [[ -z "${access_token}" ]]; then
  echo "No access token retrieved."
  exit 1
fi
echo "Got access token (truncated): ${access_token:0:12}..."

AUTH_HEADER=("Authorization: Bearer ${access_token}")

echo "3) /auth/me"
curl -fsS -b "${COOKIE_JAR}" -H "${AUTH_HEADER[@]}" "${API_BASE}/auth/me" | format_json

echo "4) /auth/refresh (uses refresh cookie)"
refresh_resp=$(curl -fsS -i -b "${COOKIE_JAR}" -c "${COOKIE_JAR}" -X POST "${API_BASE}/auth/refresh")
refresh_status=$(printf '%s\n' "${refresh_resp}" | awk 'NR==1{print $2}')
if [[ "${refresh_status}" != "200" ]]; then
  echo "Refresh failed (status ${refresh_status})"
  printf '%s\n' "${refresh_resp}"
  exit 1
fi
access_token=$(printf '%s\n' "${refresh_resp}" | sed -n '/^{/,$p' | extract_access)
AUTH_HEADER=("Authorization: Bearer ${access_token}")

echo "5) /search (query-only, embedding server-side)"
curl -fsS -b "${COOKIE_JAR}" -H "${AUTH_HEADER[@]}" -X POST "${API_BASE}/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"amparo fiscal","limit":3,"max_distance":1.5}' | format_json

echo "6) /qa (with citations)"
curl -fsS -b "${COOKIE_JAR}" -H "${AUTH_HEADER[@]}" -X POST "${API_BASE}/qa" \
  -H "Content-Type: application/json" \
  -d '{"query":"amparo fiscal","top_k":3,"max_distance":1.5}' | format_json

echo "7) /upload (requires sample.pdf)"
if [[ -f "./sample.pdf" ]]; then
  upload_resp=$(curl -fsS -b "${COOKIE_JAR}" -H "${AUTH_HEADER[@]}" -X POST "${API_BASE}/upload" -F "file=@sample.pdf")
  echo "${upload_resp}" | format_json
  job_id=$(printf '%s\n' "${upload_resp}" | sed -n 's/.*"job_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)
  if [[ -n "${job_id}" ]]; then
    echo "Upload job: ${job_id}"
    sleep 1
    curl -fsS -b "${COOKIE_JAR}" -H "${AUTH_HEADER[@]}" "${API_BASE}/upload/${job_id}" | format_json
  else
    echo "No job_id returned from upload response."
  fi
else
  echo "sample.pdf not found; skipping upload test."
fi

echo "8) synthetic eval (stubbed runner, offline-safe)"
python3 - <<'PY'
import json
import sys

from apps.agent.research_graph import get_synthetic_eval_scenarios, run_synthetic_eval


def runner(prompt: str):
    low = prompt.lower()
    area = "laboral" if "despido" in low else ("civil" if "accidente" in low or "contrato" in low else "administrativo")
    jurisdiction = "cdmx" if "cdmx" in low else ("local" if "monterrey" in low or "guadalajara" in low else "federal")
    return {
        "area_of_law": {"primary": area},
        "chosen_jurisdictions": [jurisdiction],
    }


scenarios = get_synthetic_eval_scenarios()
results = run_synthetic_eval(runner, scenarios)
if not results or not any(r.get("passed") for r in results):
    print("Synthetic eval stub failed", file=sys.stderr)
    sys.exit(1)
print(json.dumps(results, indent=2, ensure_ascii=False))
PY
