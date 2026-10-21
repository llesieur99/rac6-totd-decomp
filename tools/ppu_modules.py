"""Recover the module grouping of a PPU executable.

The PlayStation 3's loader does not jump to the program's code: the entry
point of the executable is the **module descriptor**, a table of
``(function address, module base)`` pairs that lists the functions every
linked module exports, in link order.

Two things follow from it, and both are useful to a decompilation:

* the functions of one link unit are contiguous in the table, so the table
  says which functions were linked together — the grouping into
  translation units that the SDK's compiler reacts to;
* the grouping can be checked against the code: a call to a function of
  the same unit is followed by no ``nop``, a call to a function of another
  one is followed by one.

    python tools/ppu_modules.py <eboot.elf> [--check] [--gap N]

The check compares the prediction with the code and prints the two
counts; it is the measurement that shows the grouping is meaningful.
"""

from __future__ import annotations

import argparse
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppu_elf import PpuElf, ElfError  # noqa: E402

# The descriptor is a sequence of pairs; the module base is the same for
# every entry of the executable's own modules.
PAIR = 8
# The biggest gap between two functions of one unit: a bigger one means
# another unit starts.
DEFAULT_GAP = 0x2000


def descriptor(elf: PpuElf, limit: int = 1 << 20) -> list[tuple[int, int]]:
    """The (function, module) pairs of the module descriptor."""
    entry = elf.entry
    if not entry:
        raise ElfError("the executable has no entry point")
    data = elf.read_vaddr(entry, limit)
    pairs = []
    for offset in range(0, len(data) - PAIR + 1, PAIR):
        function, module = struct.unpack_from(">II", data, offset)
        if module == 0 or function == 0:
            break
        pairs.append((function, module))
    return pairs


def group(pairs: list[tuple[int, int]], gap: int = DEFAULT_GAP) -> list[list[int]]:
    """Split the descriptor into the link units.

    The functions of one unit are contiguous in the descriptor and ascend
    in memory, so a unit ends where the addresses stop ascending or jump
    over the gap.
    """
    units: list[list[int]] = []
    current: list[int] = []
    for function, _module in pairs:
        if current and function > current[-1] and function - current[-1] < gap:
            current.append(function)
        else:
            if current:
                units.append(current)
            current = [function]
    if current:
        units.append(current)
    return units


def modules(pairs: list[tuple[int, int]]) -> list[list[int]]:
    """Split the descriptor into the runs of entries that share a TOC base.

    Each entry carries the TOC base of the module that exports the
    function.  Almost all of them carry the same one — the executable's
    own — so the runs say how many of the listed functions belong to it,
    and where the other bases start.
    """
    units: list[list[int]] = []
    current: list[int] = []
    base = None
    for function, module_base in pairs:
        if current and module_base == base:
            current.append(function)
        else:
            if current:
                units.append(current)
            current = [function]
            base = module_base
    if current:
        units.append(current)
    return units


def owner_of(units: list[list[int]]) -> dict[int, int]:
    owner: dict[int, int] = {}
    for index, unit in enumerate(units):
        for address in unit:
            owner[address] = index
    return owner


def check(elf: PpuElf, units: list[list[int]], owner: dict[int, int]) -> tuple[int, ...]:
    """Compare the grouping with the code: same unit, nop or not."""
    from capstone import Cs, CS_ARCH_PPC  # noqa: E402
    import capstone  # noqa: E402

    md = Cs(CS_ARCH_PPC, capstone.CS_MODE_64 | capstone.CS_MODE_BIG_ENDIAN)
    same_no_nop = same_nop = other_no_nop = other_nop = 0
    for unit in units:
        for address in unit:
            try:
                code = elf.read_vaddr(address, 0x40)
            except ElfError:
                continue
            insns = list(md.disasm(code, address))
            for position, insn in enumerate(insns):
                if insn.mnemonic != "bl" or position + 1 >= len(insns):
                    continue
                try:
                    target = int(insn.op_str, 16)
                except ValueError:
                    break
                if target not in owner:
                    break
                nop = insns[position + 1].mnemonic == "nop"
                if owner[target] == owner[address]:
                    if nop:
                        same_nop += 1
                    else:
                        same_no_nop += 1
                else:
                    if nop:
                        other_nop += 1
                    else:
                        other_no_nop += 1
                break
    return same_no_nop, same_nop, other_no_nop, other_nop


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("elf", help="the PPU executable to read")
    parser.add_argument("--gap", type=lambda v: int(v, 0), default=DEFAULT_GAP,
                        help="the biggest gap inside one link unit")
    parser.add_argument("--check", action="store_true",
                        help="compare the grouping with the code")
    args = parser.parse_args(argv)

    try:
        with open(args.elf, "rb") as handle:
            elf = PpuElf(handle.read(), args.elf)
    except (OSError, ElfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        pairs = descriptor(elf)
    except ElfError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not pairs:
        print("error: the module descriptor is empty", file=sys.stderr)
        return 1

    units = group(pairs, args.gap)
    owner = owner_of(units)
    sizes = sorted((len(unit) for unit in units), reverse=True)
    print(f"module descriptor at 0x{elf.entry:X}: {len(pairs)} functions")
    print(f"  {len(units)} link units, the largest ones holding "
          f"{', '.join(str(size) for size in sizes[:8])} functions")
    bases = Counter(module for _function, module in pairs)
    print(f"  {len(bases)} distinct TOC bases")
    linked = modules(pairs)
    linked_sizes = sorted((len(module) for module in linked), reverse=True)
    print(f"  {len(linked)} runs of entries sharing a TOC base, the largest holding "
          f"{', '.join(str(size) for size in linked_sizes[:4])} functions")
    if args.check:
        same_no_nop, same_nop, other_no_nop, other_nop = check(elf, units, owner)
        print("  call to a function of the same unit : "
              f"no nop {same_no_nop}, nop {same_nop}")
        print("  call to a function of another unit  : "
              f"no nop {other_no_nop}, nop {other_nop}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
