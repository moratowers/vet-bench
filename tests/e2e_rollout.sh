#!/bin/sh
# End-to-end check with no real model: two rollouts each of pair P1 (tasks T1 and C1)
# against the scripted local endpoint in tests/fake_model.py (model and judge), first with
# the read-only tools, then with the sandboxed shell, then the analysis of each run.
# It exercises what the pytest suite cannot: the null harness, the MCP tool servers,
# the interception server and the saved traces. Needs `uv` in .venv/bin
# (pip install uv); the harness's chat program fetches its own deps from PyPI once.
set -eu
cd "$(dirname "$0")/.."
PORT=8765
OUT=outputs/e2e
export PATH="$PWD/.venv/bin:$PATH" UV_CACHE_DIR="$PWD/.uv-cache"
rm -rf "$OUT"
.venv/bin/python tests/fake_model.py "$PORT" &
SERVER=$!
trap 'kill $SERVER' EXIT
sleep 1
for TOOLS in read shell; do
  .venv/bin/vf-run vet-bench -n 2 -r 2 -m fake-model -o "$OUT" --run.dir "p1-$TOOLS" \
    --client.base-url "http://127.0.0.1:$PORT/v1" \
    --env.agent.runtime.type subprocess \
    --env.taskset.task.tools "$TOOLS" \
    --env.taskset.task.judge.base-url "http://127.0.0.1:$PORT/v1" \
    --env.taskset.task.judge.model fake-judge
  .venv/bin/python analysis/pair_score.py "$OUT/p1-$TOOLS/traces.jsonl"
done
