"""Repository guard: no game data, no console keys, no build output.

The check is structural, not a substitute for reading a diff, but it catches
the mistakes that happen most often: a committed package, an extracted
executable, a licence file, a disassembly listing or a build artefact.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files and directories that must never be tracked.
FORBIDDEN_NAMES = {
    "baserom", "pkg", "eboot", "analysis", "gate", "build", ".venv", "venv",
    "__pycache__", "rap", "klic",
}

FORBIDDEN_SUFFIXES = (
    ".pkg", ".rap", ".klic", ".iso", ".elf", ".bin", ".self", ".sprx", ".prx",
    ".edat", ".sdat", ".o", ".a", ".map", ".dmp", ".core", ".asm", ".lst",
    ".dis", ".gzf", ".gpr", ".png", ".jpg", ".wav", ".at3", ".m4a", ".ogg",
    ".objdump",
)

# The console key material and the NPDRM key vault never belong here.
KEY_PATTERNS = (
    re.compile(r"NP_KLIC_KEY\s*="),
    re.compile(r"NP_KLIC_FREE\s*="),
    re.compile(r"RAP_KEY\s*="),
    re.compile(r"rap_to_rif"),
    re.compile(r"NP_RIF_KEY\s*="),
    re.compile(r"SDAT_KEY\s*="),
    re.compile(r"EDAT_KEY"),
    re.compile(r"[0-9A-Fa-f]{64}\s*,\s*\"[0-9A-Fa-f]{64}\""),
)

# Text files that may legitimately contain the words above (documentation).
KEY_EXEMPT = {
    "docs/SELF-FORMAT.md",
    "docs/STATE.md",
    "docs/ROADMAP.md",
    "tools/check_repository.py",
}

TEXT_SUFFIXES = (".py", ".md", ".json", ".yml", ".yaml", ".txt", ".cfg", ".toml", "")


def tracked_files() -> list[str]:
    """Return the repository's tracked files.

    The tracked set is the right thing to look at: the local workspace
    holds the game-derived material on purpose, and the guard must not
    punish a contributor for keeping it there.
    """
    try:
        result = subprocess.run(["git", "-C", ROOT, "ls-files"], check=True,
                                capture_output=True, text=True)
        pending = subprocess.run(
            ["git", "-C", ROOT, "ls-files", "--others", "--exclude-standard"],
            check=False, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        result = None
        pending = None
    if result is not None and result.stdout.strip():
        files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if pending is not None and pending.stdout.strip():
            # Files that are not ignored yet: they would be committed.
            files += [line.strip() for line in pending.stdout.splitlines() if line.strip()]
        return sorted(set(files))
    out = []
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".venv", "venv")]
        for name in files:
            path = os.path.join(base, name)
            out.append(os.path.relpath(path, ROOT).replace("\\", "/"))
    return sorted(out)


def check() -> list[str]:
    problems = []
    for rel in tracked_files():
        parts = rel.split("/")
        if any(part in FORBIDDEN_NAMES for part in parts[:-1]):
            problems.append(f"game-derived directory in the tree: {rel}")
        if rel.lower().endswith(FORBIDDEN_SUFFIXES):
            problems.append(f"forbidden file type: {rel}")
        if not rel.endswith(TEXT_SUFFIXES):
            continue
        if rel in KEY_EXEMPT:
            continue
        try:
            with open(os.path.join(ROOT, rel), "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            continue
        for pattern in KEY_PATTERNS:
            if pattern.search(text):
                problems.append(f"console key material in {rel} (pattern {pattern.pattern})")
                break
    return problems


def main() -> int:
    problems = check()
    if problems:
        print("repository guard: FAILED")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print("repository guard: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
