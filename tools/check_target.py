"""Check the pinned target metadata.

The file `config/target.json` is the anchor of the project: every claim
refers to it.  This check makes sure it stays well formed and internally
consistent, without needing the game itself.
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(ROOT, "config", "target.json")

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def fail(problems: list[str], message: str) -> None:
    problems.append(message)


def check() -> list[str]:
    problems: list[str] = []
    try:
        with open(TARGET, "r", encoding="utf-8") as handle:
            target = json.load(handle)
    except (OSError, ValueError) as exc:
        return [f"config/target.json cannot be read: {exc}"]

    for key in ("game", "platform", "content_id", "package", "executable",
                "ppu_elf", "segments", "matching_compiler"):
        if key not in target:
            fail(problems, f"config/target.json has no '{key}'")

    package = target.get("package", {})
    if not isinstance(package.get("size"), int) or package["size"] <= 0:
        fail(problems, "the package size is missing or not a positive integer")
    digest = package.get("sha256")
    if digest is not None and not HEX64.match(str(digest)):
        fail(problems, "the package sha256 is not 64 hexadecimal characters")
    for key in ("file_entries", "files", "directories"):
        value = package.get(key)
        if not isinstance(value, int) or value < 0:
            fail(problems, f"the package '{key}' count is missing")

    executable = target.get("executable", {})
    if not isinstance(executable.get("size"), int) or executable["size"] <= 0:
        fail(problems, "the executable size is missing")
    if not HEX64.match(str(executable.get("sha256", ""))):
        fail(problems, "the executable sha256 is not 64 hexadecimal characters")
    if executable.get("content_id") and executable["content_id"] != target.get("content_id"):
        fail(problems, "the executable's content id differs from the target's")

    elf = target.get("ppu_elf", {})
    if not isinstance(elf.get("size"), int) or elf["size"] <= 0:
        fail(problems, "the rebuilt ELF size is missing")
    if not HEX64.match(str(elf.get("sha256", ""))):
        fail(problems, "the rebuilt ELF sha256 is not 64 hexadecimal characters")
    if elf.get("size") and executable.get("size") and elf["size"] > executable["size"]:
        fail(problems, "the rebuilt ELF is larger than the executable it comes from")

    segments = target.get("segments", [])
    if not isinstance(segments, list) or not segments:
        fail(problems, "the segment list is empty")
    for segment in segments:
        for key in ("index", "vaddr", "filesz", "role"):
            if key not in segment:
                fail(problems, f"a segment has no '{key}'")

    return problems


def main() -> int:
    problems = check()
    if problems:
        print("target check: FAILED")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print("target check: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
