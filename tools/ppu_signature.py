"""Find a function in a PPU executable by its signature.

A game's engine code is shared between the studio's titles, so a function
that has been reconstructed once can be looked for in the others.  The
addresses are not the same, so the signature is taken with the *displacement
of the calls blanked*: the shape of the code is what is compared.

    python tools/ppu_signature.py <reference.elf> <address> <length> \\
        [--search target.elf ...]
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppu_elf import PpuElf, ElfError  # noqa: E402


def mask_calls(data: bytes) -> bytes:
    """Blank the displacement of every unconditional branch.

    The opcode 18 family (``b``, ``bl``, ``ba``, ``bla``) is the only one
    whose displacement depends on where the code was linked, so it is the
    only one that has to be taken out of the comparison.
    """
    out = bytearray(data)
    for i in range(0, len(out) - 3, 4):
        if (out[i] & 0xFC) == 0x48:
            out[i + 1] = out[i + 2] = out[i + 3] = 0
    return bytes(out)


def _text_range(elf: PpuElf) -> tuple[int, int]:
    """Return the (address, size) of the segment that holds the code.

    The PPU executables carry the SCE flags next to the usual permission
    bits, and a large *data* segment may have the executable bit set, so the
    segment is not chosen by its size: the code is the lowest one that
    carries any payload.
    """
    segments = [ph for ph in elf.program_headers()
                if ph.is_load and ph.filesz and (ph.flags & 0x4)]
    if not segments:
        raise ElfError("no executable segment found")
    ph = min(segments, key=lambda segment: segment.vaddr)
    return ph.vaddr, ph.filesz


def signature(elf: PpuElf, address: int, length: int) -> bytes:
    return mask_calls(elf.read_vaddr(address, length))


def find(elf: PpuElf, needle: bytes) -> list[int]:
    """The addresses where a masked signature appears."""
    vaddr, size = _text_range(elf)
    data = mask_calls(elf.read_vaddr(vaddr, size))
    hits = []
    start = 0
    while True:
        index = data.find(needle, start)
        if index < 0:
            break
        hits.append(vaddr + index)
        start = index + 4
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("reference", help="the executable the function was read in")
    parser.add_argument("address", help="the function's address, in hexadecimal")
    parser.add_argument("length", help="the function's length, in bytes")
    parser.add_argument("--search", action="append", default=[],
                        help="an executable to look in (repeatable)")
    args = parser.parse_args(argv)

    try:
        with open(args.reference, "rb") as handle:
            reference = PpuElf(handle.read(), args.reference)
    except (OSError, ElfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    needle = signature(reference, int(args.address, 16), int(args.length))

    for path in args.search:
        try:
            with open(path, "rb") as handle:
                other = PpuElf(handle.read(), path)
            hits = find(other, needle)
        except (OSError, ElfError) as exc:
            print(f"{os.path.basename(path)}: {exc}")
            continue
        if hits:
            places = ", ".join(f"0x{h:X}" for h in hits[:8])
            print(f"{os.path.basename(path)}: found at {places}")
        else:
            print(f"{os.path.basename(path)}: not found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
