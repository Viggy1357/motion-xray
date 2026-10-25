"""Offline tests for scripts/brag.sh using a fake docker binary.

No real Docker, model, or network. The wrapper is copied into a temp repo
root (path contains spaces) alongside a fake `docker` that records argv as
JSON lines and exits 0.
"""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WRAPPER = REPO / "scripts" / "brag.sh"

FAKE_DOCKER = """#!/usr/bin/env bash
log="${FAKE_DOCKER_LOG:?}"
if [ "$1" = "image" ] && [ "$2" = "inspect" ]; then
  [ "${FAKE_IMAGE_MISSING:-0}" = "1" ] && exit 1
  exit 0
fi
printf '%s\\n' "$*" >> "$log"
python3 - "$log" "$@" <<'PY'
import json,sys
log,args=sys.argv[1],sys.argv[2:]
with open(log,'a') as f: f.write(json.dumps(args)+"\\n")
PY
exit 0
"""


@pytest.fixture()
def sandbox(tmp_path):
    root = tmp_path / "repo root with spaces"
    (root / "scripts").mkdir(parents=True)
    (root / "infra" / "brag").mkdir(parents=True)
    (root / "infra" / "brag" / "Dockerfile").write_text("FROM scratch\n")
    shutil.copy(WRAPPER, root / "scripts" / "brag.sh")
    (root / "scripts" / "brag.sh").chmod(0o755)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "docker"
    fake.write_text(FAKE_DOCKER)
    fake.chmod(fake.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    log = tmp_path / "docker.log"
    env = dict(os.environ)
    env["PATH"] = f"{bindir}:{env['PATH']}"
    env["FAKE_DOCKER_LOG"] = str(log)
    env.pop("BRAG_OUTPUT_DIR", None)
    return root, log, env


def run(sandbox, *args, env_extra=None):
    root, _, env = sandbox
    e = dict(env)
    if env_extra:
        e.update(env_extra)
    return subprocess.run(["bash", "scripts/brag.sh", *args], cwd=root,
                          env=e, capture_output=True, text=True)


def runs(sandbox):
    _, log, _ = sandbox
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines() if line.startswith("[")]


@pytest.mark.parametrize("argv", [["version"], ["--version"]])
def test_version_mapped(sandbox, argv):
    r = run(sandbox, *argv)
    assert r.returncode == 0, r.stderr
    assert runs(sandbox)[0][-1] == "--version"


def test_doctor_container_flags(sandbox):
    r = run(sandbox, "doctor", "--json")
    assert r.returncode == 0, r.stderr
    args = runs(sandbox)[0]
    for flag in ("--rm", "--init", "--read-only", "--cap-drop=ALL",
                 "--security-opt=no-new-privileges", "--network"):
        assert flag in args
    assert args[args.index("--network") + 1] == "none"
    joined = " ".join(args)
    assert "--env-file" not in joined and "-v " not in joined
    assert "/work" in joined and "/work/composition" in args
    assert args[-2:] == ["doctor", "--json"]


def test_setup_build_context_infra_only(sandbox):
    r = run(sandbox, "setup")
    assert r.returncode == 0, r.stderr
    args = runs(sandbox)[0]
    assert args[0] == "build"
    ctx = args[-1]
    assert ctx.replace("\\", "/").endswith("infra/brag")
    assert "Dockerfile" in " ".join(args)


def test_no_autobuild_when_image_missing(sandbox):
    r = run(sandbox, "doctor", env_extra={"FAKE_IMAGE_MISSING": "1"})
    assert r.returncode == 3
    assert "setup" in r.stderr
    assert runs(sandbox) == []


@pytest.mark.parametrize("flag", ["--docker", "--cloud", "--lambda", "--cloudrun",
                                  "--cloud=aws", "--docker=1", "--lambda=x",
                                  "--cloudrun=eu", "--paid-media", "--heygen=api"])
def test_blocked_flags_rejected(sandbox, flag):
    r = run(sandbox, "render", flag)
    assert r.returncode == 2
    assert "rejected" in r.stderr
    assert runs(sandbox) == []


def test_unknown_command_rejected(sandbox):
    r = run(sandbox, "deploy")
    assert r.returncode == 2
    assert "not allowed" in r.stderr


@pytest.mark.parametrize("cmd", ["publish", "cloud", "login", "tts", "upgrade"])
def test_readonly_guard_blocked_commands_rejected(sandbox, cmd):
    r = run(sandbox, cmd)
    assert r.returncode == 2
    assert "not allowed" in r.stderr
    assert runs(sandbox) == []


@pytest.mark.parametrize("name", ["../evil", "/abs/path", ".hidden", "a/b",
                                  "brag-output-!bad", "brag-output-"])
def test_output_dir_traversal_rejected(sandbox, name):
    r = run(sandbox, "doctor", env_extra={"BRAG_OUTPUT_DIR": name})
    assert r.returncode == 2
    assert runs(sandbox) == []


def test_output_symlink_rejected(sandbox):
    root, _, _ = sandbox
    target = root / "elsewhere"
    target.mkdir()
    os.symlink(target, root / "brag-output")
    r = run(sandbox, "doctor")
    assert r.returncode == 2
    assert "symlink" in r.stderr


def test_composition_symlink_rejected(sandbox):
    root, _, _ = sandbox
    out = root / "brag-output"
    out.mkdir()
    target = root / "comp-target"
    target.mkdir()
    os.symlink(target, out / "composition")
    r = run(sandbox, "doctor")
    assert r.returncode == 2
    assert "symlink" in r.stderr


def test_preview_forced_port_foreground_no_open(sandbox):
    r = run(sandbox, "preview")
    assert r.returncode == 0, r.stderr
    args = runs(sandbox)[0]
    assert "--network" in args and args[args.index("--network") + 1] == "bridge"
    assert "127.0.0.1:4173:4173" in args
    assert "HYPERFRAMES_PREVIEW_HOST=0.0.0.0" in args
    tail = args[args.index("preview"):]
    assert tail[:4] == ["preview", "--port", "4173", "--foreground"]
    assert "--no-open" in tail


@pytest.mark.parametrize("flag", ["--port", "--port=9999", "--host",
                                  "--host=0.0.0.0", "--background"])
def test_preview_overrides_rejected(sandbox, flag):
    r = run(sandbox, "preview", flag)
    assert r.returncode == 2
    assert runs(sandbox) == []


@pytest.mark.parametrize("tool", ["ffmpeg", "ffprobe"])
def test_ffmpeg_ffprobe_allowed(sandbox, tool):
    r = run(sandbox, tool, "-version")
    assert r.returncode == 0, r.stderr
    args = runs(sandbox)[0]
    assert args[args.index("--network") + 1] == "none"
    assert args[-2:] == [tool, "-version"]
    joined = " ".join(args)
    assert "--env-file" not in joined and "-v " not in joined
    assert "type=bind,src=" in joined and "dst=/work" in joined
    assert joined.count("type=bind") == 1


def test_custom_output_dir_mounted(sandbox):
    r = run(sandbox, "check", env_extra={"BRAG_OUTPUT_DIR": "brag-output-run1"})
    assert r.returncode == 0, r.stderr
    joined = " ".join(runs(sandbox)[0])
    assert "brag-output-run1" in joined
