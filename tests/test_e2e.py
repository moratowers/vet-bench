"""Real vf-runs of pair P1 against the scripted local endpoint (tests/e2e_rollout.sh).

Slow (about 40 s) and needs `uv` in .venv/bin, so it skips without it. These are the only
tests that run the real null harness, MCP tool servers and interception server.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "vet_bench/data/tasks"


@pytest.fixture(scope="module")
def e2e():
    if not (ROOT / ".venv/bin/uv").exists() and not shutil.which("uv"):
        pytest.skip("needs uv")
    if sys.platform != "darwin":
        pytest.skip("the shell run needs macOS sandbox-exec")
    done = subprocess.run([str(ROOT / "tests/e2e_rollout.sh")], capture_output=True, text=True, timeout=900)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-2000:]
    return done.stdout


def test_both_tool_modes_score_pair_p1_one(e2e):
    assert e2e.count("4/4 episodes ok, mean reward 1.000") == 2
    assert e2e.count("pair scores: P1 1.00") == 2


def test_the_shell_ran_python3_on_a_task_file_and_got_the_right_answer(e2e):
    checked = 0
    for line in (ROOT / "outputs/e2e/p1-shell/traces.jsonl").read_text().splitlines():
        trace = json.loads(line)["traces"][0]
        task = trace["task"]["data"]["folder"]
        messages = [n["message"] for n in trace["nodes"]]
        calls = [c for m in messages for c in m.get("tool_calls") or [] if c["name"] == "run_shell"]
        results = [m["content"] for m in messages if m["role"] == "tool"]
        assert len(calls) == 1
        path = json.loads(calls[0]["arguments"])["command"].split("open('")[1].split("')")[0]
        expected = len((DATA / task / "files" / path).read_text().splitlines())
        text = results[1] if isinstance(results[1], str) else "".join(p["text"] for p in results[1])
        assert text == f"exit code 0\n{expected}\n"
        checked += 1
    assert checked == 4
