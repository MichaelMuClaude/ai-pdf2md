import subprocess
import sys


def test_missing_file_returns_error():
    result = subprocess.run(
        [sys.executable, "-m", "ai_pdf2md.cli", "convert", "/no/such/file.pdf"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "no such file" in result.stderr


def test_version_flag():
    result = subprocess.run(
        [sys.executable, "-m", "ai_pdf2md.cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
