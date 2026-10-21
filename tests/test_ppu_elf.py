"""Tests for the PPU ELF reader, on a synthetic ELF64 big-endian file."""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import ppu_elf  # noqa: E402


def shdr(name_off, sh_type, flags, addr, offset, size, link=0, info=0, align=1, entsize=0):
    return (struct.pack(">II", name_off, sh_type)
            + struct.pack(">QQQQ", flags, addr, offset, size)
            + struct.pack(">II", link, info)
            + struct.pack(">QQ", align, entsize))


def build_elf():
    """A small ELF64 big-endian file with five sections and three symbols."""
    #            0        1     7           17           26
    shstrtab = b"\x00.text\x00.shstrtab\x00.symtab\x00.strtab\x00"
    strtab = b"\x00_start\x00_helper\x00data\x00"
    text = b"\x60\x00\x00\x00" * 4
    symbols = b""
    for name_off, value, size, info in ((1, 0x10000, 16, 0x12), (8, 0x10010, 8, 0x12),
                                        (15, 0, 0, 0)):
        symbols += struct.pack(">IBBHQQ", name_off, info, 0, 1, value, size)
    text_off = 0x300
    strtab_off = text_off + len(text)
    shstrtab_off = strtab_off + len(strtab)
    sym_off = shstrtab_off + len(shstrtab)
    shoff = 0x100
    shnum = 5

    headers = b""
    headers += shdr(0, 0, 0, 0, 0, 0)                                     # null
    headers += shdr(1, 1, 0x6, 0x10000, text_off, len(text))              # .text
    headers += shdr(26, 3, 0, 0, strtab_off, len(strtab))                  # .strtab
    headers += shdr(17, 2, 0, 0, sym_off, len(symbols), link=2, info=1,
                    align=8, entsize=24)                                   # .symtab
    headers += shdr(7, 3, 0, 0, shstrtab_off, len(shstrtab))                # .shstrtab

    out = bytearray(0x400)
    out[shoff:shoff + len(headers)] = headers
    out[0:16] = b"\x7fELF\x02\x02\x01\x66" + b"\x00" * 8
    struct.pack_into(">HH", out, 0x10, 2, 0x15)
    struct.pack_into(">Q", out, 0x18, 0x10000)          # entry
    struct.pack_into(">Q", out, 0x20, 0x40)             # e_phoff
    struct.pack_into(">Q", out, 0x28, shoff)            # e_shoff
    struct.pack_into(">HHH", out, 0x34, 64, 56, 0)      # ehsize, phentsize, phnum
    struct.pack_into(">HHH", out, 0x3A, 64, shnum, 4)   # shentsize, shnum, shstrndx
    out[text_off:text_off + len(text)] = text
    out[strtab_off:strtab_off + len(strtab)] = strtab
    out[shstrtab_off:shstrtab_off + len(shstrtab)] = shstrtab
    out[sym_off:sym_off + len(symbols)] = symbols
    return bytes(out)


class PpuElfTest(unittest.TestCase):
    def setUp(self):
        self.elf = ppu_elf.PpuElf(build_elf(), "synthetic")

    def test_header(self):
        self.assertEqual(self.elf.entry, 0x10000)
        self.assertEqual(self.elf.shnum, 5)
        self.assertEqual(self.elf.shstrndx, 4)

    def test_sections_have_names(self):
        names = [s.name for s in self.elf.sections()]
        self.assertEqual(names[1], ".text")
        self.assertEqual(names[4], ".shstrtab")

    def test_symbols(self):
        symbols = self.elf.symbols()
        self.assertEqual(len(symbols), 3)
        self.assertEqual(symbols[0].name, "_start")
        self.assertEqual(symbols[0].value, 0x10000)
        self.assertEqual(symbols[0].size, 16)
        self.assertTrue(symbols[0].is_function)

    def test_functions_are_sorted(self):
        functions = self.elf.functions()
        self.assertEqual([f.name for f in functions], ["_start", "_helper"])

    def test_rejects_a_little_endian_file(self):
        data = bytearray(build_elf())
        data[5] = 1
        with self.assertRaises(ppu_elf.ElfError):
            ppu_elf.PpuElf(bytes(data), "synthetic")


if __name__ == "__main__":
    unittest.main()
