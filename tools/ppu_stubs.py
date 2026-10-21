"""The TOC-adjusting call rule of the SDK 1.9.0.

The SDK's own header says it:

    /* place a nop after the call so that the linker can restore the TOC
       pointer if a TOC adjusting call stub is needed.  */

The retail build proves it: every call whose target is one of the
TOC-adjusting stubs carries `ld r2, 0x28(r1)` in its delay slot, and no
other call does.

    python ppu_stubs.py <eboot.elf> [--list]
"""
from __future__ import annotations

import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppu_elf import PpuElf, ElfError  # noqa: E402

# The stub's shape: std r2,0x28(r1) / addis r2,r2,N / addi r2,r2,N / b <target>
STUB_FIRST = 0xF8410028
BRANCH = 0x48000000


def is_stub(words: list[int], index: int) -> bool:
    """True when the four words at `index` are a TOC-adjusting stub."""
    if index + 3 >= len(words):
        return False
    if words[index] != STUB_FIRST:
        return False
    # addis r2, r2, N
    if (words[index + 1] & 0xFFFF0000) != 0x3C420000:
        return False
    # addi r2, r2, N
    if (words[index + 2] & 0xFFFF0000) != 0x38420000:
        return False
    # b <target>
    if (words[index + 3] & 0xFC000003) != BRANCH:
        return False
    return True


def stub_table(elf: PpuElf, start: int, end: int) -> list[int]:
    """The addresses of the TOC-adjusting stubs in the given range."""
    data = elf.read_vaddr(start, end - start)
    words = list(struct.unpack(f">{len(data) // 4}I", data))
    stubs = []
    index = 0
    while index + 3 < len(words):
        if is_stub(words, index):
            stubs.append(start + index * 4)
            index += 4
        else:
            index += 1
    return stubs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("elf", help="the PPU ELF to read")
    parser.add_argument("--start", default="0x10200", help="where the stub table starts")
    parser.add_argument("--end", default="0x14340", help="where the stub table ends")
    parser.add_argument("--list", action="store_true", help="list the stubs")
    args = parser.parse_args(argv)

    try:
        with open(args.elf, "rb") as handle:
            elf = PpuElf(handle.read(), args.elf)
    except (OSError, ElfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    start = int(args.start, 0)
    end = int(args.end, 0)
    stubs = stub_table(elf, start, end)
    print(f"the TOC-adjusting stubs between 0x{start:X} and 0x{end:X}: {len(stubs)}")
    if stubs:
        print(f"  from 0x{stubs[0]:X} to 0x{stubs[-1]:X}")
        span = stubs[-1] - stubs[0] + 16
        print(f"  {span} bytes, {span // 16} bytes each")
    if args.list:
        for address in stubs:
            print(f"  0x{address:08X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
