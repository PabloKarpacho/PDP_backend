import os
from pathlib import Path
import stat
import subprocess
import textwrap


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "deploy-backend.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content))
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _prepare_fake_app_dir(tmp_path: Path) -> Path:
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / ".git").mkdir()
    (app_dir / ".env").write_text("APP_PORT=8001\n")
    return app_dir


def _prepare_fake_bin(tmp_path: Path, curl_mode: str) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    _write_executable(
        bin_dir / "git",
        """#!/usr/bin/env bash
        echo "$*" >> "$TEST_STATE_DIR/git.log"
        exit 0
        """,
    )
    _write_executable(
        bin_dir / "docker",
        """#!/usr/bin/env bash
        echo "$*" >> "$TEST_STATE_DIR/docker.log"
        exit 0
        """,
    )
    _write_executable(
        bin_dir / "sleep",
        """#!/usr/bin/env bash
        echo "$*" >> "$TEST_STATE_DIR/sleep.log"
        exit 0
        """,
    )

    if curl_mode == "eventual-success":
        curl_body = """
        count_file="$TEST_STATE_DIR/curl-count"
        count=0
        if [ -f "$count_file" ]; then
          count="$(cat "$count_file")"
        fi
        count="$((count + 1))"
        printf '%s' "$count" > "$count_file"
        if [ "$count" -lt 3 ]; then
          echo "curl: (56) Recv failure: Connection reset by peer" >&2
          exit 56
        fi
        exit 0
        """
    else:
        curl_body = """
        echo "curl: (56) Recv failure: Connection reset by peer" >&2
        exit 56
        """

    _write_executable(
        bin_dir / "curl",
        f"""#!/usr/bin/env bash
        {textwrap.dedent(curl_body).strip()}
        """,
    )

    return bin_dir


def _run_script(
    tmp_path: Path, curl_mode: str, readiness_attempts: int = 4
) -> subprocess.CompletedProcess[str]:
    app_dir = _prepare_fake_app_dir(tmp_path)
    bin_dir = _prepare_fake_bin(tmp_path, curl_mode=curl_mode)
    env = os.environ.copy()
    env.update(
        {
            "APP_DIR": str(app_dir),
            "BRANCH": "main",
            "READINESS_ATTEMPTS": str(readiness_attempts),
            "READINESS_INTERVAL_SECONDS": "1",
            "READINESS_TIMEOUT_SECONDS": "1",
            "TEST_STATE_DIR": str(tmp_path / "state"),
            "PATH": f"{bin_dir}:{env['PATH']}",
        }
    )
    return subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_deploy_backend_waits_for_readiness_without_leaking_curl_errors(
    tmp_path: Path,
) -> None:
    result = _run_script(tmp_path, curl_mode="eventual-success")

    assert result.returncode == 0
    assert (
        "==> Waiting for readiness at http://localhost:8001/actuator/health/readiness"
        in result.stdout
    )
    assert "Readiness probe failed (attempt 1/4), retrying in 1s" in result.stdout
    assert "Readiness probe failed (attempt 2/4), retrying in 1s" in result.stdout
    assert "Backend is ready" in result.stdout
    assert "Recv failure: Connection reset by peer" not in result.stdout
    assert result.stderr == ""


def test_deploy_backend_reports_readiness_timeout_cleanly(tmp_path: Path) -> None:
    result = _run_script(tmp_path, curl_mode="always-fail", readiness_attempts=2)

    assert result.returncode == 1
    assert "Readiness probe failed (attempt 1/2), retrying in 1s" in result.stdout
    assert "Readiness probe failed (attempt 2/2)" in result.stdout
    assert (
        "Backend failed readiness check: http://localhost:8001/actuator/health/readiness"
        in result.stdout
    )
    assert "Recv failure: Connection reset by peer" not in result.stdout
    assert result.stderr == ""
