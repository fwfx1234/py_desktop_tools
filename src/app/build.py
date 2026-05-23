from __future__ import annotations

import shutil
import subprocess
import sys

from .paths import project_root


def main() -> int:
    root = project_root()
    spec_path = root / "tools" / "suishou.spec"
    if not spec_path.exists():
        print(f"PyInstaller spec not found: {spec_path}", file=sys.stderr)
        return 1

    uv = shutil.which("uv")
    if uv is None:
        print("uv executable not found in PATH.", file=sys.stderr)
        return 1

    command = [
        uv,
        "run",
        "--group",
        "build",
        "python",
        "-m",
        "PyInstaller",
        str(spec_path.relative_to(root)),
        "--noconfirm",
        *sys.argv[1:],
    ]
    return subprocess.run(command, cwd=root).returncode


if __name__ == "__main__":
    raise SystemExit(main())
