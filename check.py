#!/usr/bin/env python3
import shutil
import subprocess

STEPS = [
    ("ty", ["ty", "check", "src"]),
    ("ruff", ["ruff", "check", "src"]),
    ("ruff", ["ruff", "format", "--check", "src"])
]


def run(name: str, cmd: list[str]) -> None:
    print(f"----- {name} -----")
    if shutil.which(cmd[0]) is None:
        print(
            f"'{cmd[0]}' not found. Please install with `uv sync` or your package manager."
        )
        return
    subprocess.run(cmd, check=False)


def main() -> None:
    for name, cmd in STEPS:
        run(name, cmd)


if __name__ == "__main__":
    main()