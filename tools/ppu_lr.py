"""Measure which register a PPU executable keeps its link register in.

The SDK's prologue moves the link register into a general register before
storing it (``mflr rX`` / ``std rX, offset(r1)``), and the epilogue reads it
back before ``mtlr``.  Which register that is depends on the code, and it
is a good way to compare two executables built by the same compiler: the
distribution over a whole executable says more than a single function.

    python tools/ppu_lr.py <eboot.elf> [--json]

The measure counts the functions whose prologue is the SDK's own shape:
``stdu r1, -N(r1)`` followed by ``mflr rX``.  The epilogue is counted
separately: the register that receives the link register before the
``mtlr``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppu_elf import PpuElf, ElfError  # noqa: E402
from ppu_funcs import build_catalogue  # noqa: E402

# ``stdu r1, -N(r1)``: opcode 62, rD = rS = rA = 1.
STDU_R1 = 0xF8210000
# ``mflr rX``: opcode 31, the destination register in bits 21-25.
MFLR = 0x7C0802A6
MFLR_MASK = 0xFC1FFFFF


def u32(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 4], "big")


def prologue_register(data: bytes) -> int | None:
    """The register of the ``mflr`` of an SDK prologue, if that is what it is."""
    if len(data) < 8:
        return None
    if u32(data, 0) & 0xFFFF0000 != STDU_R1:
        return None
    word = u32(data, 4)
    if word & MFLR_MASK != MFLR:
        return None
    return (word >> 21) & 0x1F


def epilogue_register(data: bytes) -> int | None:
    """The register that receives the link register before the ``mtlr``."""
    words = [u32(data, i) for i in range(0, len(data) - 3, 4)]
    for index, word in enumerate(words):
        # ``mtlr rX``: opcode 31, extended opcode 0x8 (the link register).
        if (word & 0xFC1FFFFF) != 0x7C0803A6:
            continue
        register = (word >> 21) & 0x1F
        for previous in range(index - 1, max(-1, index - 4), -1):
            other = words[previous]
            # ``ld rX, d(r1)``: the offset form, the displacement in bits
            # 0-15, the base register in bits 16-20, the destination in
            # bits 21-25, the opcode in bits 26-31.
            if ((other & 0xFC010000) == 0xE8010000
                    and ((other >> 16) & 0x1F) == 1
                    and ((other >> 21) & 0x1F) == register):
                return register
        return None
    return None


def measure(elf: PpuElf, limit: int = 0x400) -> dict:
    """The distribution of the link register's register over the executable."""
    prologue = Counter()
    epilogue = Counter()
    functions = 0
    for address, _kind, _evidence in build_catalogue(elf):
        try:
            data = elf.read_vaddr(address, limit)
        except ElfError:
            continue
        functions += 1
        register = prologue_register(data)
        if register is not None:
            prologue[register] += 1
        register = epilogue_register(data)
        if register is not None:
            epilogue[register] += 1
    return {
        "functions": functions,
        "prologue": dict(sorted(prologue.items())),
        "epilogue": dict(sorted(epilogue.items())),
    }


def show(name: str, counts: dict) -> None:
    total = sum(counts.values())
    if not total:
        print(f"  {name}: none")
        return
    parts = ", ".join(f"r{register} {100 * count / total:.0f}%"
                       for register, count in sorted(counts.items(),
                                                     key=lambda item: -item[1]))
    print(f"  {name}: {total} functions - {parts}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("elf", help="the PPU executable to measure")
    parser.add_argument("--json", action="store_true", help="write the counts as JSON")
    args = parser.parse_args(argv)

    try:
        with open(args.elf, "rb") as handle:
            elf = PpuElf(handle.read(), args.elf)
    except (OSError, ElfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result = measure(elf)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"{os.path.basename(args.elf)}: {result['functions']} functions")
    show("prologue", result["prologue"])
    show("epilogue ", result["epilogue"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
