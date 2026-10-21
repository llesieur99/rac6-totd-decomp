"""Tests for the link register's register measurement, on synthetic code."""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import ppu_elf  # noqa: E402
import ppu_lr  # noqa: E402


def stdu(offset):
    """stdu r1, -offset(r1)"""
    return 0xF8210000 | ((-offset) & 0xFFFF)


def mflr(register):
    return 0x7C0802A6 | (register << 21)


def mtlr(register):
    return 0x7C0803A6 | (register << 21)


def ld_r1(register, displacement):
    """ld rX, displacement(r1)"""
    return 0xE8010000 | (displacement & 0xFFFF) | (register << 21)


def blr():
    return 0x4E800020


def build_elf(functions):
    """An ELF with one executable segment holding the given functions."""
    code = b"".join(struct.pack(">I", word) for word in functions)
    off = 0x200
    out = bytearray(0x400 + len(code))
    out[0:16] = b"\x7fELF\x02\x02\x01\x66" + b"\x00" * 8
    struct.pack_into(">HH", out, 0x10, 2, 0x15)
    struct.pack_into(">Q", out, 0x18, 0x10000)
    struct.pack_into(">Q", out, 0x20, 0x40)
    struct.pack_into(">Q", out, 0x28, 0x100)
    struct.pack_into(">HHH", out, 0x34, 64, 56, 1)
    struct.pack_into(">HHH", out, 0x3A, 64, 1, 0)
    out[0x40:0x40 + 56] = (struct.pack(">II", 1, 0x5)
                           + struct.pack(">6Q", off, 0x10000, 0x10000, len(code), len(code), 0x10000))
    out[off:off + len(code)] = code
    return bytes(out)


class LinkRegisterTest(unittest.TestCase):
    def test_the_prologue_register_is_read(self):
        self.assertEqual(ppu_lr.prologue_register(
            struct.pack(">II", stdu(0x70), mflr(4))), 4)
        self.assertEqual(ppu_lr.prologue_register(
            struct.pack(">II", stdu(0x70), mflr(0))), 0)

    def test_a_function_without_the_sdk_shape_has_no_prologue(self):
        self.assertIsNone(ppu_lr.prologue_register(
            struct.pack(">II", 0x60000000, mflr(0))))
        self.assertIsNone(ppu_lr.prologue_register(b"\x00" * 4))

    def test_the_epilogue_register_is_read(self):
        code = struct.pack(">III", ld_r1(3, 0x90), mtlr(3), blr())
        self.assertEqual(ppu_lr.epilogue_register(code), 3)
        code = struct.pack(">III", ld_r1(0, 0x80), mtlr(0), blr())
        self.assertEqual(ppu_lr.epilogue_register(code), 0)

    def test_the_measurement_counts_both(self):
        elf = ppu_elf.PpuElf(build_elf([
            stdu(0x70), mflr(0), ld_r1(0, 0x80), mtlr(0), blr(),
            stdu(0x90), mflr(4), ld_r1(4, 0xA0), mtlr(4), blr(),
        ]), "synthetic")
        result = ppu_lr.measure(elf)
        self.assertEqual(result["prologue"], {0: 1, 4: 1})
        self.assertEqual(result["epilogue"], {0: 1, 4: 1})


if __name__ == "__main__":
    unittest.main()
