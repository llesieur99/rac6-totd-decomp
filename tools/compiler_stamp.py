"""Read the compiler stamps out of a PPU executable.

A GCC-built program carries the compiler's identification in the
``.comment`` section, once per linked object.  The retail PlayStation 3
executables are no exception: their stamps name the exact compiler and the
exact SDK revision that produced them, which is the first thing a matching
decompilation needs to know.

The tool only reads strings; it never decodes code.

    python tools/compiler_stamp.py <eboot.elf>
    python tools/compiler_stamp.py <eboot.elf> --libraries
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppu_elf import PpuElf, ElfError  # noqa: E402

STAMP = re.compile(rb"GCC: \([^\x00]{0,120}\)")

# The libraries a retail executable usually carries, and how they name
# themselves.
LIBRARIES = (
    rb"Dinkumware[^\x00]{0,60}",
    rb"Lua 5\.[0-9.]+[^\x00]{0,40}",
    rb"zlib [0-9.]+[^\x00]{0,30}",
    rb"inflate [0-9.]+[^\x00]{0,30}",
    rb"deflate [0-9.]+[^\x00]{0,30}",
    rb"Copyright \(c\) [0-9]{4}-[0-9]{4} by P\.J\. Plauger[^\x00]{0,40}",
)


def compiler_stamps(data: bytes) -> Counter:
    """The distinct compiler stamps, with how many times each appears."""
    return Counter(match.group().decode("latin1") for match in STAMP.finditer(data))


def library_stamps(data: bytes) -> Counter:
    """The distinct library identification strings."""
    found = Counter()
    for pattern in LIBRARIES:
        for match in re.finditer(pattern, data):
            found[match.group().decode("latin1")] += 1
    return found


def cmd_stamps(elf: PpuElf, args: argparse.Namespace) -> int:
    stamps = compiler_stamps(elf.data)
    if not stamps:
        print("no compiler stamp found")
        return 1
    print(f"{len(stamps)} distinct compiler stamp(s):")
    for stamp, count in stamps.most_common():
        print(f"  {count:5d} x {stamp}")
    return 0


def cmd_libraries(elf: PpuElf, args: argparse.Namespace) -> int:
    for name, count in library_stamps(elf.data).most_common():
        print(f"  {count:5d} x {name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("elf", help="path to the rebuilt PPU ELF")
    parser.add_argument("--libraries", action="store_true",
                        help="also report the libraries the executable carries")
    args = parser.parse_args(argv)
    try:
        with open(args.elf, "rb") as handle:
            elf = PpuElf(handle.read(), args.elf)
    except (OSError, ElfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    status = cmd_stamps(elf, args)
    if args.libraries:
        cmd_libraries(elf, args)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
