from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_backend_dockerfile_allows_non_root_bind_to_port_80() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text()

    assert "libcap2-bin" in dockerfile
    assert "setcap 'cap_net_bind_service=+ep'" in dockerfile
    assert "USER appuser" in dockerfile
    assert "EXPOSE 80" in dockerfile
