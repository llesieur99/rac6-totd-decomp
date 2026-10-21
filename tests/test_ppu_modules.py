"""Tests for the module descriptor reader, on a synthetic executable."""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import ppu_elf  # noqa: E402
import ppu_modules  # noqa: E402

ENTRY = 0x10000


def build_elf(pairs, code=b""):
    """An ELF whose entry point is a module descriptor."""
    table = b"".join(struct.pack(">II", function, module) for function, module in pairs)
    off = 0x200
    size = off + len(table) + len(code)
    out = bytearray(max(0x400, size))
    out[0:16] = b"\x7fELF\x02\x02\x01\x66" + b"\x00" * 8
    struct.pack_into(">HH", out, 0x10, 2, 0x15)
    struct.pack_into(">Q", out, 0x18, ENTRY)
    struct.pack_into(">Q", out, 0x20, 0x40)
    struct.pack_into(">Q", out, 0x28, 0x100)
    struct.pack_into(">HHH", out, 0x34, 64, 56, 1)
    struct.pack_into(">HHH", out, 0x3A, 64, 1, 0)
    out[0x40:0x40 + 56] = (struct.pack(">II", 1, 0x5)
                           + struct.pack(">6Q", off, ENTRY, ENTRY, len(table) + len(code),
                                         len(table) + len(code), ENTRY))
    out[off:off + len(table)] = table
    out[off + len(table):off + len(table) + len(code)] = code
    return bytes(out)


class ModuleDescriptorTest(unittest.TestCase):
    def test_the_pairs_are_read(self):
        elf = ppu_elf.PpuElf(build_elf([(0x10280, 0xD34770), (0x102A8, 0xD34770)]), "synthetic")
        self.assertEqual(ppu_modules.descriptor(elf), [(0x10280, 0xD34770), (0x102A8, 0xD34770)])

    def test_the_descriptor_stops_at_the_first_empty_entry(self):
        elf = ppu_elf.PpuElf(build_elf([(0x10280, 0xD34770), (0, 0), (0x102A8, 0xD34770)]),
                             "synthetic")
        self.assertEqual(len(ppu_modules.descriptor(elf)), 1)

    def test_the_units_follow_the_addresses(self):
        pairs = [(0x10280, 1), (0x102A8, 1), (0x20000, 1), (0x20010, 1)]
        units = ppu_modules.group(pairs, gap=0x1000)
        self.assertEqual(units, [[0x10280, 0x102A8], [0x20000, 0x20010]])

    def test_a_gap_splits_a_unit(self):
        pairs = [(0x10280, 1), (0x102A8, 1), (0x30000, 1)]
        units = ppu_modules.group(pairs, gap=0x1000)
        self.assertEqual(units, [[0x10280, 0x102A8], [0x30000]])

    def test_the_owner_of_every_function(self):
        pairs = [(0x10280, 1), (0x102A8, 1), (0x20000, 1)]
        owner = ppu_modules.owner_of(ppu_modules.group(pairs, gap=0x1000))
        self.assertEqual(owner[0x10280], owner[0x102A8])
        self.assertNotEqual(owner[0x10280], owner[0x20000])


if __name__ == "__main__":
    unittest.main()
