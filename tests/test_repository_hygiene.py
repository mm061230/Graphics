import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_ONLY_PREFIXES = [
    "_ref/",
    "input_images/",
    "output_results/",
    "result/",
    "work/",
]


def test_publish_history_excludes_local_runtime_directories():
    git_binary = shutil.which("git") or shutil.which("git.exe")
    if git_binary is None:
        raise AssertionError("git executable is required for repository hygiene audit")

    completed = subprocess.run(
        [git_binary, "ls-files"],
        cwd=PROJECT_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    tracked = [line.strip().replace("\\", "/") for line in completed.stdout.splitlines() if line.strip()]
    leaked = [path for path in tracked if any(path.startswith(prefix) for prefix in LOCAL_ONLY_PREFIXES)]

    assert leaked == []
