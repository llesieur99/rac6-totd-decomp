"""Tests for the PPU function-boundary scanner, on a synthetic code segment."""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import ppu_elf  # noqa: E402
import ppu_funcs  # noqa: E402

# stdu r1, -0x70(r1) / mflr r0 / stdu r1, -0x50(r1) / bl +0x20
STDU = 0xF821FF90
MFLR = 0x7C0802A6
BL = 0x48000021


def shdr(name_off, sh_type, flags, addr, offset, size):
    return (struct.pack(">II", name_off, sh_type)
            + struct.pack(">QQQQ", flags, addr, offset, size)
            + struct.pack(">II", 0, 0)
            + struct.pack(">QQ", 1, 0))


def build_elf(words=None):
    """An ELF with one executable segment holding a few instructions."""
    if words is None:
        words = [
            0x38600000,      # li r3, 0
            STDU,            # stdu r1, -0x70(r1)
            MFLR,            # mflr r0
            0x4E800020,      # blr
            0x60000000,      # nop
            MFLR,            # mflr r0
            STDU,            # stdu r1, -0x60(r1)
            BL,              # bl +0x20
            0x60000000,      # nop
        ]
    code = b"".join(struct.pack(">I", w) for w in words)
    off = 0x200
    out = bytearray(0x400)
    out[0:16] = b"\x7fELF\x02\x02\x01\x66" + b"\x00" * 8
    struct.pack_into(">HH", out, 0x10, 2, 0x15)
    struct.pack_into(">Q", out, 0x18, 0x10000)
    struct.pack_into(">Q", out, 0x20, 0x40)
    struct.pack_into(">Q", out, 0x28, 0x100)
    struct.pack_into(">HHH", out, 0x34, 64, 56, 1)
    struct.pack_into(">HHH", out, 0x3A, 64, 1, 0)
    # one program header: PT_LOAD, read + execute
    out[0x40:0x40 + 56] = (struct.pack(">II", 1, 0x5)
                           + struct.pack(">6Q", off, 0x10000, 0x10000, len(code), len(code), 0x10000))
    out[off:off + len(code)] = code
    return bytes(out)


class PpuFuncsTest(unittest.TestCase):
    def setUp(self):
        self.elf = ppu_elf.PpuElf(build_elf(), "synthetic")

    def test_prologue_candidates(self):
        addresses = [c.address for c in ppu_funcs.prologue_candidates(self.elf)]
        # the stdu at +4 (followed by mflr) and the stdu at +0x18 (preceded by mflr)
        self.assertEqual(addresses, [0x10004, 0x10018])

    def test_call_targets(self):
        addresses = [c.address for c in ppu_funcs.call_targets(self.elf)]
        self.assertEqual(addresses, [0x1003C])

    def test_the_link_register_may_be_saved_in_any_register(self):
        # ``mflr r12``: the compiler uses any general register, and a
        # narrower mask would miss every function that uses one of the
        # higher ones
        elf = ppu_elf.PpuElf(build_elf([0xF821FF91, 0x7C0802A6 | (12 << 21)]),
                             "high register")
        self.assertEqual([c.address for c in ppu_funcs.prologue_candidates(elf)],
                         [0x10000])

    def test_an_absolute_branch_is_not_a_call(self):
        # ``bla 0x20000``: the target is an address, not a displacement, so
        # it names no function the caller calls.
        elf = ppu_elf.PpuElf(build_elf([0x48000003, 0x4E800020]), "absolute")
        self.assertEqual([c.address for c in ppu_funcs.call_targets(elf)], [])

    def test_catalogue_merges_both(self):
        rows = ppu_funcs.build_catalogue(self.elf)
        table = {address: evidence for address, _kind, evidence in rows}
        self.assertEqual(table[0x10004], "prologue")
        self.assertEqual(table[0x10018], "prologue")
        self.assertEqual(table[0x1003C], "call")


if __name__ == "__main__":
    unittest.main()
