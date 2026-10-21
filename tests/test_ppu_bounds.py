"""Tests for the flow-based boundary recovery, on synthetic code."""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import ppu_bounds  # noqa: E402

STDU = 0xF821FF91
MFLR = 0x7C0802A6
NOP = 0x60000000
BLR = 0x4E800020
GP = 0xD34770


def build_elf(words, descriptor=None, vaddr=0x10000, entry=None):
    """An ELF with one loadable segment holding code and a descriptor table."""
    code = b"".join(struct.pack(">I", w) for w in words)
    table = b""
    if descriptor is not None:
        table = b"".join(struct.pack(">II", address, GP) for address in descriptor)
    off = 0x200
    out = bytearray(0x400 + len(code) + len(table))
    out[0:16] = b"\x7fELF\x02\x02\x01\x66" + b"\x00" * 8
    struct.pack_into(">HH", out, 0x10, 2, 0x15)
    struct.pack_into(">Q", out, 0x18, entry if entry is not None else vaddr)
    struct.pack_into(">Q", out, 0x20, 0x40)
    struct.pack_into(">Q", out, 0x28, 0x100)
    struct.pack_into(">HHH", out, 0x34, 64, 56, 1)
    struct.pack_into(">HHH", out, 0x3A, 64, 1, 0)
    out[0x40:0x40 + 56] = (struct.pack(">II", 1, 0x5)
                           + struct.pack(">6Q", off, vaddr, vaddr,
                                         len(code) + len(table), len(code) + len(table), vaddr))
    out[off:off + len(code)] = code
    out[off + len(code):off + len(code) + len(table)] = table
    return bytes(out)


class FlowBoundsTest(unittest.TestCase):
    def test_a_call_and_a_return_bound_a_function(self):
        words = [
            STDU, MFLR, NOP,      # the first function's opening
            BLR,
            STDU, MFLR, NOP,      # the second function's opening
            BLR,
        ]
        elf = ppu_bounds.Elf(build_elf(words), "synthetic")
        result = ppu_bounds.analyse(elf, 0x10000, 0x40)
        starts = {func.start for func in result.functions}
        self.assertIn(0x10000, starts)
        self.assertIn(0x10010, starts)

    def test_an_indirect_branch_is_not_a_return(self):
        # a ``bctr`` must not be taken for a return: only the branches that
        # come back are terminals
        words = [
            STDU, MFLR, NOP,
            0x4E800420,           # bctr
            NOP,
        ]
        elf = ppu_bounds.Elf(build_elf(words), "synthetic")
        result = ppu_bounds.analyse(elf, 0x10000, 0x20)
        self.assertNotIn(0x10004, {func.start for func in result.functions})

    def test_the_descriptor_is_read(self):
        elf = ppu_bounds.Elf(build_elf([BLR], descriptor=[0x10000, 0x10004],
                                       entry=0x10004), "synthetic")
        found = ppu_bounds.opd_functions(elf, elf.code_ranges())
        self.assertEqual(sorted(found), [0x10000, 0x10004])


if __name__ == "__main__":
    unittest.main()
