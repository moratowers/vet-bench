"""The shell tool's sandbox, probed the way vet-bench probes its subject sandbox.

Each forbidden attempt must come back as an error from the operating system (a nonzero
exit and "Operation not permitted" or a failed connection), and its side effect must be
absent: no file written, no connection received. Attempts are made both as shell commands
and as Python with computed paths, because a blocklist on command text would miss those.
No model is called. macOS only, like the tool itself.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import threading
import time
from importlib.resources import files
from pathlib import Path

import pytest

import verifiers.v1 as vf
from vet_bench import shell
from vet_bench.shell import ShellToolset
from vet_bench.taskset import VetTaskset, VetTasksetConfig

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="sandbox-exec is macOS only")

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(str(files("vet_bench").joinpath("data")))
REFUSED = (
    "Operation not permitted",  # the sandbox's EPERM, as Python and the Unix tools print it
    "Couldn't connect to server",  # curl's wording for the same EPERM on connect
    "nodename nor servname provided",  # name lookup refused
    "Could not resolve host",  # curl's wording for the same
)


def task(task_id: str):
    tasks = VetTaskset(VetTasksetConfig(id="vet-bench")).load()
    return next(t for t in tasks if t.key == task_id)


@pytest.fixture
def server():
    """A shell server on task T1's scratch copy; removed afterwards."""
    s = ShellToolset(vf.ToolsetConfig())
    asyncio.run(s.setup_task(task("T1").data))
    yield s
    shell.shutil.rmtree(s.run_dir, ignore_errors=True)


def run(server: ShellToolset, command: str) -> tuple[str, str]:
    """(exit code, output) of one run_shell call."""
    reply = asyncio.run(server.run_shell(command))
    head, _, body = reply.partition("\n")
    return head.removeprefix("exit code "), body


def py(code: str) -> str:
    """A python3 -c command line for `code` (no single quotes inside `code`)."""
    return f"python3 -c '{code}'"


def assert_refused(server: ShellToolset, command: str) -> None:
    code, out = run(server, command)
    assert code != "0", f"allowed: {command!r} -> {out!r}"
    assert any(r in out for r in REFUSED), out


# ---------------------------------------------------------------- what must work


def test_python_one_liner_on_a_task_file(server):
    csv_path = DATA / "tasks/P1/T1/files/scan/band_winrate.csv"
    lines = csv_path.read_text().splitlines()[1:]
    expected = sum(int(line.split(",")[1]) for line in lines)
    code, out = run(server, py(
        "import csv; rows = list(csv.DictReader(open(\"scan/band_winrate.csv\")));"
        " print(sum(int(r[\"n\"]) for r in rows))"
    ))
    assert (code, out.strip()) == ("0", str(expected))
    assert expected == 1630  # the rubric's pooled n for T1


def test_writes_inside_the_copy_work_and_leave_the_task_untouched(server):
    code, out = run(server, "echo changed > scan/scan.log && cat scan/scan.log")
    assert (code, out.strip()) == ("0", "changed")
    assert "changed" not in (DATA / "tasks/P1/T1/files/scan/scan.log").read_text()
    assert "changed" in server.read_file("scan/scan.log")


def test_a_command_is_stopped_at_the_time_limit(server, monkeypatch):
    monkeypatch.setattr(shell, "TIMEOUT_SECONDS", 2)
    code, _ = run(server, "sleep 30")
    assert code.startswith("none (stopped after 2 s)")


DETACH = "import os, time; os.fork() or (os.setsid(), time.sleep(20), os._exit(0)); "


def test_a_detached_child_holding_the_output_cannot_hold_the_call(server, monkeypatch):
    """The shell runs past the limit and is killed; its detached child keeps the output."""
    monkeypatch.setattr(shell, "TIMEOUT_SECONDS", 3)
    start = time.monotonic()
    code, out = run(server, py(DETACH + "print(\"started\", flush=True); time.sleep(30)"))
    elapsed = time.monotonic() - start
    assert elapsed < 3 + 8, elapsed  # the limit plus the bounded waits after it
    assert code.startswith("none (stopped after 3 s)") and "started" in out


def test_a_finished_shell_with_a_background_child_reports_its_real_exit_code(server, monkeypatch):
    """The shell exits at once; only a detached child holds the output. No false timeout,
    no false "output cut", and no wait for the time limit."""
    monkeypatch.setattr(shell, "TIMEOUT_SECONDS", 10)
    start = time.monotonic()
    code, out = run(server, py(DETACH + "print(\"parent done\")"))
    elapsed = time.monotonic() - start
    assert elapsed < 6, elapsed
    assert code == "0" and "parent done" in out
    assert "output cut" not in out
    assert "a background process still holds the output open" in out


def test_output_is_cut(server):
    _, out = run(server, py("print(\"x\" * 50000)"))
    assert out.endswith(f"[output cut at {shell.OUTPUT_LIMIT} characters]")
    assert out.count("x") == shell.OUTPUT_LIMIT


# ---------------------------------------------------------------- the network


def test_no_internet(server):
    assert_refused(server, py("import socket; socket.create_connection((\"1.1.1.1\", 443), timeout=5)"))
    assert_refused(server, py("import socket; socket.getaddrinfo(\"example.com\", 443)"))
    assert_refused(server, "curl -sS -m 5 https://example.com")


def test_no_launching_apps_or_scripts_that_would_run_outside_the_sandbox(server):
    assert_refused(server, "open --help")
    assert_refused(server, "osascript -e 1")
    assert_refused(server, py("import subprocess; subprocess.run([\"/usr/bin/open\", \"--help\"], check=True)"))


def test_no_connection_to_a_listening_local_server(server):
    """The model endpoint, the judge and the tool servers listen on 127.0.0.1."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    listener.settimeout(8)
    port = listener.getsockname()[1]
    received: list[bool] = []
    thread = threading.Thread(target=lambda: received.append(bool(_accept(listener))))
    thread.start()
    assert_refused(server, py(f"import socket; socket.create_connection((\"127.0.0.1\", {port}), timeout=5)"))
    assert_refused(server, f"curl -sS -m 5 http://127.0.0.1:{port}/")
    thread.join()
    listener.close()
    assert received == [False]


def _accept(listener: socket.socket) -> bool:
    try:
        conn, _ = listener.accept()
        conn.close()
        return True
    except TimeoutError:
        return False


# ---------------------------------------------------------------- reads outside the copy


def test_no_reads_beside_or_above_the_copy(server):
    (server.run_dir / "canary.txt").write_text("canary")
    assert_refused(server, "cat ../canary.txt")
    assert_refused(server, "ls ..")
    assert_refused(server, py("import os; print(os.listdir(os.pardir))"))
    assert_refused(server, py("import os; print(open(os.path.join(os.pardir, \"canary.txt\")).read())"))
    assert_refused(server, f"ls {shell.SCRATCH_ROOT}")


def test_no_reads_of_other_tasks_answers_or_the_host(server):
    twin = DATA / "tasks/P1/C1/files/scan/scan.log"  # the other side of this pair
    for path in (twin, DATA / "tasks.json", ROOT / "tests/fixtures/answers/T1/R.md",
                 ROOT / "vet_bench/taskset.py", Path.home() / ".zshrc"):
        assert_refused(server, f"cat {path}")
        parts = json.dumps(str(path).split("/"))  # a path the command text never spells out
        assert_refused(server, py(f"print(open(\"/\".join({parts})).read())"))
    assert_refused(server, f"ls {Path.home()}")


def test_no_reads_of_another_rollouts_copy(server):
    other = ShellToolset(vf.ToolsetConfig())
    asyncio.run(other.setup_task(task("C1").data))
    try:
        assert_refused(server, f"cat {other.root}/scan/scan.log")
        assert_refused(server, f"ls {other.root}")
    finally:
        shell.shutil.rmtree(other.run_dir, ignore_errors=True)


def test_a_new_rollout_removes_copies_left_by_exited_servers():
    stale = shell.SCRATCH_ROOT / "deadbeef0000"
    young = shell.SCRATCH_ROOT / "deadbeef0001"
    for folder in (stale, young):
        (folder / "work").mkdir(parents=True, exist_ok=True)
        (folder / "pid").write_text("999999")  # no such process
    hour_ago = time.time() - 3600
    os.utime(stale, (hour_ago, hour_ago))
    s = ShellToolset(vf.ToolsetConfig())
    asyncio.run(s.setup_task(task("T1").data))
    try:
        assert not stale.exists() and s.run_dir.exists()
        assert young.exists()  # inside the grace period: never swept
    finally:
        for folder in (s.run_dir, young):
            shell.shutil.rmtree(folder, ignore_errors=True)


def _setups(n: int) -> list[str]:
    """Run n setups in this process; report any whose copy is missing or incomplete."""
    problems, made = [], []
    for _ in range(n):
        s = ShellToolset(vf.ToolsetConfig())
        try:
            asyncio.run(s.setup_task(task("T1").data))
        except Exception as e:  # noqa: BLE001 - every failure is the finding
            problems.append(repr(e))
            continue
        made.append(s.run_dir)
        if not (s.root / "scan/scan.log").is_file():
            problems.append(f"incomplete {s.run_dir}")
    for folder in made:  # all checked before any is removed, so sweeps overlap with setups
        if not (folder / "pid").is_file():
            problems.append(f"swept while live {folder}")
        shell.shutil.rmtree(folder, ignore_errors=True)
    return problems


def test_hundreds_of_concurrent_setups_never_sweep_each_other():
    """The review's stress shape: 24 processes doing 15 setups each, all at once."""
    from concurrent.futures import ProcessPoolExecutor

    with ProcessPoolExecutor(max_workers=24) as pool:
        results = list(pool.map(_setups, [15] * 24))
    problems = [p for r in results for p in r]
    assert problems == [], problems[:5]


def test_list_files_does_not_follow_links_the_model_makes(server):
    other = ShellToolset(vf.ToolsetConfig())
    asyncio.run(other.setup_task(task("C1").data))
    try:
        targets = {"to_tasks_json": DATA / "tasks.json", "to_other_copy": other.root / "scan/scan.log"}
        for name, target in targets.items():
            code, out = run(server, f"ln -s {target} {name}")
            assert code == "0", out
        entries = {e["path"]: e for e in server.list_files()}
        for name in targets:
            assert entries[name] == {"path": name, "type": "link"}  # no size, no line count
            assert server.read_file(name).startswith("error:")
    finally:
        shell.shutil.rmtree(other.run_dir, ignore_errors=True)


def test_a_link_swapped_in_after_the_check_is_refused(server, monkeypatch):
    """The race the recheck found: lstat sees a regular file, then a link to tasks.json takes
    its place before the open. O_NOFOLLOW refuses the open, so nothing about the target leaks."""
    from vet_bench import tools

    os.symlink(DATA / "tasks.json", server.root / "swapped")
    regular = os.lstat(server.root / "scan/scan.log")
    real_lstat = os.lstat
    monkeypatch.setattr(tools.os, "lstat", lambda p: regular if str(p).endswith("swapped") else real_lstat(p))
    entries = {e["path"]: e for e in server.list_files()}
    assert entries["swapped"] == {"path": "swapped", "type": "link"}


def test_an_entry_that_vanishes_mid_listing_is_skipped(server, monkeypatch):
    from vet_bench import tools

    (server.root / "gone.txt").write_text("x")
    real_walk = tools.walk

    def walk_then_delete(root):
        found = real_walk(root)
        (server.root / "gone.txt").unlink()
        return found

    monkeypatch.setattr(tools, "walk", walk_then_delete)
    paths = [e["path"] for e in server.list_files()]
    assert "gone.txt" not in paths and "scan/scan.log" in paths


def test_no_other_processes(server):
    assert_refused(server, "ps aux")


# ---------------------------------------------------------------- writes outside the copy


def test_no_writes_outside_the_copy(server):
    targets = [server.run_dir / "escape.txt", shell.SCRATCH_ROOT / "escape.txt",
               Path("/private/tmp/escape.txt"), ROOT / "escape.txt", Path.home() / "escape.txt"]
    for target in targets:
        assert_refused(server, f"echo x > {target}")
        assert not target.exists()
    assert_refused(server, py("open(__import__(\"os\").path.join(__import__(\"os\").pardir, \"e.txt\"), \"w\")"))
    assert not (server.run_dir / "e.txt").exists()
