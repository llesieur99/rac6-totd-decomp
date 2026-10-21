"""Tests for the TOC-adjusting stub reader."""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import ppu_stubs  # noqa: E402


def word(value):
    return struct.pack(">I", value)


class PpuStubsTest(unittest.TestCase):
    def test_is_stub(self):
        # std r2,0x28(r1) / addis r2,r2,2 / addi r2,r2,-0x14 / b <target>
        stub = [0xF8410028, 0x3C420002, 0x3842FFEC, 0x4885438C]
        self.assertTrue(ppu_stubs.is_stub(stub, 0))

    def test_is_not_stub(self):
        # the same shape with a wrong first instruction
        stub = [0xF841002C, 0x3C420002, 0x3842FFEC, 0x4885438C]
        self.assertFalse(ppu_stubs.is_stub(stub, 0))
        # a function that starts like a stub but branches somewhere else
        stub = [0xF8410028, 0x3C420002, 0x3842FFEC, 0x7C0802A6]
        self.assertFalse(ppu_stubs.is_stub(stub, 0))
        # too short
        self.assertFalse(ppu_stubs.is_stub([0xF8410028], 0))

    def test_branches_only(self):
        # a conditional branch is not a stub's tail jump
        stub = [0xF8410028, 0x3C420002, 0x3842FFEC, 0x40820010]
        self.assertFalse(ppu_stubs.is_stub(stub, 0))


if __name__ == "__main__":
    unittest.main()
