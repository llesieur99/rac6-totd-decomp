"""Tests for the signature search, on two synthetic executables."""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import ppu_elf  # noqa: E402
import ppu_signature  # noqa: E402

STDU = 0xF821FF91
MFLR = 0x7C0802A6


def build_elf(words, vaddr=0x10000, size=0x400):
    """An ELF with one executable segment holding the given instructions."""
    code = b"".join(struct.pack(">I", w) for w in words)
    off = 0x200
    out = bytearray(size)
    out[0:16] = b"\x7fELF\x02\x02\x01\x66" + b"\x00" * 8
    struct.pack_into(">HH", out, 0x10, 2, 0x15)
    struct.pack_into(">Q", out, 0x18, vaddr)
    struct.pack_into(">Q", out, 0x20, 0x40)
    struct.pack_into(">Q", out, 0x28, 0x100)
    struct.pack_into(">HHH", out, 0x34, 64, 56, 1)
    struct.pack_into(">HHH", out, 0x3A, 64, 1, 0)
    out[0x40:0x40 + 56] = (struct.pack(">II", 1, 0x5)
                           + struct.pack(">6Q", off, vaddr, vaddr, len(code), len(code), vaddr))
    out[off:off + len(code)] = code
    return bytes(out)


# The function as it is in one game: two calls, to 0x105A8 and 0x67AF8.
BODY = [
    STDU,           # stdu r1, -0x70(r1)
    MFLR,           # mflr r0
    0xF8010080,     # std r0, 0x80(r1)
    0x4800039D,     # bl 0x105A8
    0x60000000,     # nop
    0x480578E5,     # bl 0x67AF8
    0x60000000,     # nop
    0xE8010080,     # ld r0, 0x80(r1)
    0x7C0803A6,     # mtlr r0
    0x38210070,     # addi r1, r1, 0x70
    0x4E800020,     # blr
]


class MaskCallsTest(unittest.TestCase):
    def test_the_call_displacement_is_blanked(self):
        masked = ppu_signature.mask_calls(b"".join(struct.pack(">I", w) for w in BODY))
        # the two calls keep their opcode, lose their displacement
        self.assertEqual(masked[12:16], b"\x48\x00\x00\x00")
        self.assertEqual(masked[20:24], b"\x48\x00\x00\x00")

    def test_the_other_instructions_are_untouched(self):
        raw = b"".join(struct.pack(">I", w) for w in BODY)
        masked = ppu_signature.mask_calls(raw)
        self.assertEqual(masked[0:12], raw[0:12])
        self.assertEqual(masked[28:], raw[28:])


class SignatureSearchTest(unittest.TestCase):
    def test_the_same_code_is_found_in_another_build(self):
        reference = ppu_elf.PpuElf(build_elf(BODY), "reference")
        needle = ppu_signature.signature(reference, 0x10000, len(BODY) * 4)

        # another build: the same code, linked at another address, with the
        # calls pointing somewhere else
        other = list(BODY)
        other[3] = 0x48000001
        other[5] = 0x48000002
        target = ppu_elf.PpuElf(build_elf(other, vaddr=0x20000), "other")

        self.assertEqual(ppu_signature.find(target, needle), [0x20000])

    def test_different_code_is_not_found(self):
        reference = ppu_elf.PpuElf(build_elf(BODY), "reference")
        needle = ppu_signature.signature(reference, 0x10000, len(BODY) * 4)
        elsewhere = ppu_elf.PpuElf(build_elf([0x4E800020] * 12), "other")
        self.assertEqual(ppu_signature.find(elsewhere, needle), [])


if __name__ == "__main__":
    unittest.main()
