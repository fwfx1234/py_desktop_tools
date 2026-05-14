from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def restart_current_app() -> subprocess.Popen:
    """Start a fresh app process and let the caller quit the current QApplication."""
    if getattr(sys, "frozen", False):
        args = [sys.executable, *sys.argv[1:]]
        cwd = Path.cwd()
        env = None
    else:
        repo_root = Path(__file__).resolve().parents[2]
        src_root = repo_root / "src"
        args = [sys.executable, "-m", "app.main"]
        cwd = repo_root
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            str(src_root)
            if not existing_pythonpath
            else f"{src_root}{os.pathsep}{existing_pythonpath}"
        )

    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    return subprocess.Popen(
        args,
        cwd=str(cwd),
        env=env,
        close_fds=True,
        creationflags=creationflags,
    )
