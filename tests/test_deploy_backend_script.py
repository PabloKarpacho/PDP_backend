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


def _prepare_fake_app_dir(tmp_path: Path, env_content: str = "APP_PORT=8001\n") -> Path:
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / ".git").mkdir()
    (app_dir / ".env").write_text(env_content)
    return app_dir


def _prepare_fake_bin(tmp_path: Path, docker_up_mode: str) -> Path:
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
        f"""#!/usr/bin/env bash
        echo "$*" >> "$TEST_STATE_DIR/docker.log"
        if [ "$1 $2 $3 $4" = "compose up -d --force-recreate" ] && [ "{docker_up_mode}" = "fail-backend-start" ]; then
          exit 1
        fi
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
    _write_executable(
        bin_dir / "uv",
        """#!/usr/bin/env bash
        echo "$*" >> "$TEST_STATE_DIR/uv.log"
        if [ "$1 $2 $3 $4" = "run python -m src.services.keycloak_secret" ]; then
          echo "aws-secret-password"
          exit 0
        fi
        exit 0
        """,
    )

    return bin_dir


def _run_script(
    tmp_path: Path,
    docker_up_mode: str = "success",
    env_content: str = "APP_PORT=8001\n",
) -> subprocess.CompletedProcess[str]:
    app_dir = _prepare_fake_app_dir(tmp_path, env_content=env_content)
    bin_dir = _prepare_fake_bin(tmp_path, docker_up_mode=docker_up_mode)
    env = os.environ.copy()
    env.update(
        {
            "APP_DIR": str(app_dir),
            "BRANCH": "main",
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


def test_deploy_backend_recreates_backend_container_without_readiness_probe(
    tmp_path: Path,
) -> None:
    result = _run_script(tmp_path)
    docker_log = (tmp_path / "state" / "docker.log").read_text()

    assert result.returncode == 0
    assert "==> Removing previous backend container" in result.stdout
    assert "==> Starting backend" in result.stdout
    assert "Waiting for readiness" not in result.stdout
    assert "compose rm -fsv pdp-backend" in docker_log
    assert "compose up -d --force-recreate pdp-backend" in docker_log
    assert result.stderr == ""


def test_deploy_backend_reports_backend_start_failure_cleanly(tmp_path: Path) -> None:
    result = _run_script(tmp_path, docker_up_mode="fail-backend-start")
    docker_log = (tmp_path / "state" / "docker.log").read_text()

    assert result.returncode == 1
    assert "==> Backend container status" in result.stdout
    assert "==> Recent backend logs" in result.stdout
    assert "Backend container failed to start" in result.stdout
    assert "compose up -d --force-recreate pdp-backend" in docker_log
    assert result.stderr == ""


def test_deploy_backend_resolves_keycloak_password_from_aws_secret(
    tmp_path: Path,
) -> None:
    result = _run_script(
        tmp_path,
        env_content=(
            "APP_PORT=8001\n"
            "AWS_POSTGRES_REGION=eu-north-1\n"
            "KC_DB_PASSWORD=\n"
            "KC_DB_AWS_SECRET_ID=secret-id\n"
        ),
    )
    uv_log = (tmp_path / "state" / "uv.log").read_text()

    assert result.returncode == 0
    assert (
        "==> Resolving Keycloak database password from AWS Secrets Manager"
        in result.stdout
    )
    assert "run python -m src.services.keycloak_secret" in uv_log
