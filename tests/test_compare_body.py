"""Tests for the byte comparison used by the body gate."""

import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import compare_body  # noqa: E402


def build_object(payload: bytes, name: str = ".text") -> bytes:
    """A minimal big-endian ELF64 object with one section."""
    shstrtab = b"\x00.text\x00.shstrtab\x00"
    text_off = 0x100
    strtab_off = text_off + len(payload)
    shstrtab_off = strtab_off + 4
    shoff = 0x40
    out = bytearray(0x200)
    out[0:16] = b"\x7fELF\x02\x02\x01\x66" + b"\x00" * 8
    struct.pack_into(">HH", out, 0x10, 1, 0x15)
    struct.pack_into(">Q", out, 0x18, 0)
    struct.pack_into(">Q", out, 0x20, 0)
    struct.pack_into(">Q", out, 0x28, shoff)
    struct.pack_into(">HHH", out, 0x34, 64, 56, 0)
    struct.pack_into(">HHH", out, 0x3A, 64, 3, 2)
    headers = b""
    headers += (struct.pack(">II", 0, 0) + struct.pack(">QQQQ", 0, 0, 0, 0)
                + struct.pack(">II", 0, 0) + struct.pack(">QQ", 1, 0))
    headers += (struct.pack(">II", 1, 1) + struct.pack(">QQQQ", 6, 0, text_off, len(payload))
                + struct.pack(">II", 0, 0) + struct.pack(">QQ", 1, 0))
    headers += (struct.pack(">II", 11, 3) + struct.pack(">QQQQ", 0, 0, shstrtab_off, len(shstrtab))
                + struct.pack(">II", 0, 0) + struct.pack(">QQ", 1, 0))
    out[shoff:shoff + len(headers)] = headers
    out[text_off:text_off + len(payload)] = payload
    out[strtab_off:strtab_off + 4] = b"\x00\x00\x00\x00"
    out[shstrtab_off:shstrtab_off + len(shstrtab)] = shstrtab
    return bytes(out)


class CompareBodyTest(unittest.TestCase):
    def test_sections_are_read(self):
        with tempfile.NamedTemporaryFile(suffix=".o", delete=False) as handle:
            handle.write(build_object(b"\x60\x00\x00\x00"))
            path = handle.name
        try:
            sections = compare_body.read_object_sections(path)
            self.assertIn(".text", sections)
            self.assertEqual(sections[".text"], b"\x60\x00\x00\x00")
        finally:
            os.unlink(path)

    def test_identical_bytes_match(self):
        index, retail, candidate = compare_body.compare(b"\x01\x02\x03\x04", b"\x01\x02\x03\x04", 0)
        self.assertEqual(index, -1)

    def test_first_difference_is_reported(self):
        index, retail, candidate = compare_body.compare(b"\x01\x02\x03\x04", b"\x01\xff\x03\x04", 0)
        self.assertEqual(index, 1)
        self.assertEqual(retail[index], 0x02)
        self.assertEqual(candidate[index], 0xFF)

    def test_length_difference_is_reported(self):
        index, retail, candidate = compare_body.compare(b"\x01\x02", b"\x01\x02\x03", 0)
        self.assertEqual(index, 2)


if __name__ == "__main__":
    unittest.main()
