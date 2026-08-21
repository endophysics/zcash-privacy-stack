from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_cli_image_inherits_compiled_evidence_stage() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM test AS cli" in dockerfile
