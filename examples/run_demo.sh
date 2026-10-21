#!/usr/bin/env bash
# Lite demo: presence and allowed values on two fixtures.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
log=$(mktemp)
pid=""
cleanup() {
  if [[ -n "${pid}" ]]; then
    kill "${pid}" 2>/dev/null || true
    wait "${pid}" 2>/dev/null || true
  fi
  rm -f "${log}"
}
trap cleanup EXIT
python3 deliverables/fixture_server.py --root examples/fixtures --port 0 >"${log}" &
pid=$!
port=""
for _ in $(seq 1 50); do
  if grep -q '^PORT ' "${log}"; then
    port=$(awk '/^PORT /{print $2; exit}' "${log}")
    break
  fi
  if ! kill -0 "${pid}" 2>/dev/null; then
    break
  fi
  sleep 0.05
done
if [[ -z "${port}" ]]; then
  echo "error: fixture server did not print a port" >&2
  exit 1
fi
base="http://127.0.0.1:${port}"
echo "=== lite good ==="
python3 deliverables/check_headers_lite.py --url "${base}/good" --policy deliverables/baseline_policy.json
echo "=== lite missing ==="
set +e
python3 deliverables/check_headers_lite.py --url "${base}/missing" --policy deliverables/baseline_policy.json
echo "missing_exit:$?"
set -e
