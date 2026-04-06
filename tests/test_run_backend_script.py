import os
from pathlib import Path
import stat
import subprocess
import textwrap


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run-backend.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content))
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _prepare_fake_venv(tmp_path: Path) -> tuple[Path, Path]:
    venv_dir = tmp_path / "venv"
    bin_dir = venv_dir / "bin"
    bin_dir.mkdir(parents=True)
    state_dir = tmp_path / "state"
    state_dir.mkdir()

    _write_executable(
        bin_dir / "uvicorn",
        """#!/usr/bin/env bash
        printf '%s\n' "$@" > "$TEST_STATE_DIR/uvicorn-args.log"
        exit 0
        """,
    )
    _write_executable(
        bin_dir / "python",
        """#!/usr/bin/env bash
        exit 0
        """,
    )
    return venv_dir, state_dir


def test_run_backend_enables_ssl_when_explicitly_configured(tmp_path: Path) -> None:
    venv_dir, state_dir = _prepare_fake_venv(tmp_path)
    cert_dir = tmp_path / "certs"
    cert_dir.mkdir()
    cert_file = cert_dir / "cert.pem"
    key_file = cert_dir / "key.pem"
    cert_file.write_text("cert")
    key_file.write_text("key")

    env = os.environ.copy()
    env.update(
        {
            "UV_PROJECT_ENVIRONMENT": str(venv_dir),
            "UVICORN_SSL_MODE": "true",
            "UVICORN_SSL_CERTFILE": str(cert_file),
            "UVICORN_SSL_KEYFILE": str(key_file),
            "TEST_STATE_DIR": str(state_dir),
        }
    )

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    uvicorn_args = (state_dir / "uvicorn-args.log").read_text()

    assert result.returncode == 0
    assert "Uvicorn SSL enabled." in result.stdout
    assert f"--ssl-certfile={cert_file}" in uvicorn_args
    assert f"--ssl-keyfile={key_file}" in uvicorn_args


def test_run_backend_skips_ssl_in_auto_mode_when_files_missing(tmp_path: Path) -> None:
    venv_dir, state_dir = _prepare_fake_venv(tmp_path)

    env = os.environ.copy()
    env.update(
        {
            "UV_PROJECT_ENVIRONMENT": str(venv_dir),
            "UVICORN_SSL_MODE": "auto",
            "UVICORN_SSL_CERTFILE": str(tmp_path / "missing-cert.pem"),
            "UVICORN_SSL_KEYFILE": str(tmp_path / "missing-key.pem"),
            "TEST_STATE_DIR": str(state_dir),
        }
    )

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    uvicorn_args = (state_dir / "uvicorn-args.log").read_text()

    assert result.returncode == 0
    assert "Uvicorn SSL skipped" in result.stdout
    assert "--ssl-certfile=" not in uvicorn_args
    assert "--ssl-keyfile=" not in uvicorn_args
