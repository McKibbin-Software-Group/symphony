import os
import subprocess
import sys
from pathlib import Path


def test_processor_commandline_interface(model_file: Path, capsys):
    repo_root = Path(__file__).resolve().parents[1]

    env = os.environ.copy()
    src_path = repo_root / "src"
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(src_path) if not existing else f"{src_path}{os.pathsep}{existing}"
    )

    result = subprocess.run(
        [sys.executable, "-m", "symphony.processor", str(model_file)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
    )

    # Re-emit captured output so CLI logging is visible during test runs.
    with capsys.disabled():
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)

    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert result.stdout.strip(), "Expected the processor to emit output."
