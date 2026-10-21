"""Reader for the PS3 PPU executable (the big-endian PowerPC ELF of an eboot).

The tool reads a decrypted PPU ELF and reports its structure: program
headers, section headers, the symbol table and a catalogue of the functions
it names.  It needs nothing but the Python standard library.

    python tools/ppu_elf.py info     <eboot.elf>
    python tools/ppu_elf.py sections <eboot.elf>
    python tools/ppu_elf.py symbols  <eboot.elf> [--limit N]
    python tools/ppu_elf.py catalogue <eboot.elf> [--out FILE]

PPU specifics worth knowing:

* The ELF is ELF64, big-endian, and its ``e_machine`` is ``EM_NONE`` (0); the
  target is the Cell BEAT (PowerPC) core, not a classic Gekko.
* The program headers carry the SCE flag bits (``PF_SPU_X``, ``PF_RSX_R``,
  ...) in ``p_flags`` next to the usual permission bits.
* Two synthetic program headers describe the SPU's export table and the
  RSX/graphics segment; they carry no payload in the file.
"""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from typing import Iterator, Sequence

SHT_SYMTAB = 2
SHT_STRTAB = 3
SHT_NOBITS = 8
SHT_DYNSYM = 11

SHF_WRITE = 0x1
SHF_ALLOC = 0x2
SHF_EXECINSTR = 0x4

STT_FUNC = 2

# SCE-specific program-header flag bits.
PF_SPU_X = 0x00100000
PF_SPU_W = 0x00200000
PF_SPU_R = 0x00400000
PF_RSX_X = 0x01000000
PF_RSX_W = 0x02000000
PF_RSX_R = 0x04000000

PT_LOAD = 1
PT_TLS = 7
PT_SCE_SEGSYM = 0x700000A8


class ElfError(Exception):
    """The file is not a readable PPU ELF."""


@dataclass(frozen=True)
class ProgramHeader:
    index: int
    type: int
    flags: int
    offset: int
    vaddr: int
    paddr: int
    filesz: int
    memsz: int
    align: int

    @property
    def is_load(self) -> bool:
        return self.type == PT_LOAD


@dataclass(frozen=True)
class SectionHeader:
    index: int
    name_offset: int
    type: int
    flags: int
    addr: int
    offset: int
    size: int
    link: int
    info: int
    addralign: int
    entsize: int
    name: str = ""


@dataclass(frozen=True)
class Symbol:
    index: int
    name: str
    value: int
    size: int
    info: int
    other: int
    shndx: int

    @property
    def type(self) -> int:
        return self.info & 0xF

    @property
    def binding(self) -> int:
        return self.info >> 4

    @property
    def is_function(self) -> bool:
        return self.type == STT_FUNC


class PpuElf:
    """A PS3 PPU executable."""

    def __init__(self, data: bytes, name: str = "<memory>"):
        self.data = data
        self.name = name
        if data[:4] != b"\x7fELF":
            raise ElfError("not an ELF file")
        if data[4] != 2:
            raise ElfError("not a 64-bit ELF")
        if data[5] != 2:
            raise ElfError("not a big-endian ELF")
        self.entry = struct.unpack_from(">Q", data, 0x18)[0]
        self.phoff = struct.unpack_from(">Q", data, 0x20)[0]
        self.shoff = struct.unpack_from(">Q", data, 0x28)[0]
        (self.phentsize, self.phnum, self.shentsize,
         self.shnum, self.shstrndx) = struct.unpack_from(">5H", data, 0x36)
        self._sections: list[SectionHeader] | None = None

    # -- program headers ---------------------------------------------------
    def program_headers(self) -> list[ProgramHeader]:
        out = []
        for i in range(self.phnum):
            off = self.phoff + i * self.phentsize
            p_type, p_flags = struct.unpack_from(">II", self.data, off)
            p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = \
                struct.unpack_from(">6Q", self.data, off + 8)
            out.append(ProgramHeader(i, p_type, p_flags, p_offset, p_vaddr,
                                     p_paddr, p_filesz, p_memsz, p_align))
        return out

    # -- section headers ---------------------------------------------------
    def sections(self) -> list[SectionHeader]:
        if self._sections is not None:
            return self._sections
        raw = []
        for i in range(self.shnum):
            off = self.shoff + i * self.shentsize
            if off + self.shentsize > len(self.data):
                break
            name_offset, sh_type = struct.unpack_from(">II", self.data, off)
            flags, addr, sh_offset, size = struct.unpack_from(">4Q", self.data, off + 8)
            link, info, addralign, entsize = struct.unpack_from(">IIQQ", self.data, off + 0x28)
            raw.append(SectionHeader(i, name_offset, sh_type, flags, addr,
                                     sh_offset, size, link, info, addralign, entsize))
        if raw and self.shstrndx < len(raw):
            strtab = raw[self.shstrndx]
            names = []
            for sec in raw:
                start = strtab.offset + sec.name_offset
                end = self.data.find(b"\x00", start)
                names.append(self.data[start:end].decode("ascii", "replace")
                             if 0 <= start < len(self.data) else "")
            raw = [SectionHeader(s.index, s.name_offset, s.type, s.flags, s.addr,
                                 s.offset, s.size, s.link, s.info, s.addralign,
                                 s.entsize, names[i]) for i, s in enumerate(raw)]
        self._sections = raw
        return raw

    def section(self, name: str) -> SectionHeader | None:
        for sec in self.sections():
            if sec.name == name:
                return sec
        return None

    def section_data(self, section: SectionHeader) -> bytes:
        if section.type == SHT_NOBITS:
            return b""
        return self.data[section.offset:section.offset + section.size]

    # -- symbols -----------------------------------------------------------
    def symbols(self) -> list[Symbol]:
        out: list[Symbol] = []
        for sec in self.sections():
            if sec.type not in (SHT_SYMTAB, SHT_DYNSYM) or not sec.size:
                continue
            if sec.link >= len(self.sections()):
                continue
            strtab = self.sections()[sec.link]
            count = sec.size // (sec.entsize or 24)
            for i in range(count):
                off = sec.offset + i * (sec.entsize or 24)
                if off + 24 > len(self.data):
                    break
                st_name, st_info, st_other, st_shndx = \
                    struct.unpack_from(">IBBH", self.data, off)
                st_value, st_size = struct.unpack_from(">QQ", self.data, off + 8)
                start = strtab.offset + st_name
                end = self.data.find(b"\x00", start)
                name = self.data[start:end].decode("ascii", "replace") \
                    if 0 <= start < len(self.data) else ""
                out.append(Symbol(i, name, st_value, st_size, st_info, st_other, st_shndx))
        return out

    def functions(self) -> list[Symbol]:
        """The named functions of the executable, sorted by address."""
        funcs = [s for s in self.symbols() if s.is_function and s.name and s.value]
        funcs.sort(key=lambda s: s.value)
        return funcs

    # -- helpers -----------------------------------------------------------
    def segment_for(self, vaddr: int) -> ProgramHeader | None:
        for ph in self.program_headers():
            if not ph.is_load:
                continue
            if ph.vaddr <= vaddr < ph.vaddr + ph.memsz:
                return ph
        return None

    def read_vaddr(self, vaddr: int, length: int) -> bytes:
        ph = self.segment_for(vaddr)
        if ph is None:
            raise ElfError(f"no segment holds 0x{vaddr:X}")
        start = ph.offset + (vaddr - ph.vaddr)
        return self.data[start:start + length]


def _load(path: str) -> PpuElf:
    with open(path, "rb") as handle:
        return PpuElf(handle.read(), path)


def cmd_info(elf: PpuElf, args: argparse.Namespace) -> int:
    print(f"file         : {elf.name}")
    print(f"size         : {len(elf.data)}")
    print(f"entry        : 0x{elf.entry:X}")
    print(f"program hdrs : {elf.phnum}")
    print(f"section hdrs : {elf.shnum}")
    print("program headers:")
    for ph in elf.program_headers():
        flags = []
        if ph.flags & PF_SPU_X:
            flags.append("SPU_X")
        if ph.flags & PF_SPU_W:
            flags.append("SPU_W")
        if ph.flags & PF_SPU_R:
            flags.append("SPU_R")
        if ph.flags & PF_RSX_X:
            flags.append("RSX_X")
        if ph.flags & PF_RSX_W:
            flags.append("RSX_W")
        if ph.flags & PF_RSX_R:
            flags.append("RSX_R")
        print(f"  [{ph.index}] type=0x{ph.type:08X} off=0x{ph.offset:X} "
              f"vaddr=0x{ph.vaddr:X} filesz=0x{ph.filesz:X} memsz=0x{ph.memsz:X} "
              f"flags=0x{ph.flags:X} {','.join(flags)}")
    return 0


def cmd_sections(elf: PpuElf, args: argparse.Namespace) -> int:
    for sec in elf.sections():
        print(f"[{sec.index:2d}] {sec.name:20s} type={sec.type:2d} flags=0x{sec.flags:X} "
              f"addr=0x{sec.addr:08X} off=0x{sec.offset:08X} size=0x{sec.size:08X}")
    return 0


def cmd_symbols(elf: PpuElf, args: argparse.Namespace) -> int:
    symbols = elf.symbols()
    print(f"{len(symbols)} symbols")
    for sym in symbols[:args.limit] if args.limit else symbols:
        print(f"  0x{sym.value:08X} size={sym.size:6d} type={sym.type} "
              f"shndx={sym.shndx:3d} {sym.name}")
    return 0


def cmd_catalogue(elf: PpuElf, args: argparse.Namespace) -> int:
    lines = ["address\tsize\tname"]
    for sym in elf.functions():
        lines.append(f"0x{sym.value:08X}\t{sym.size}\t{sym.name}")
    text = "\n".join(lines) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"wrote {args.out}: {len(lines) - 1} functions")
    else:
        sys.stdout.write(text)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("elf", help="path to the decrypted PPU ELF")
        return p

    add("info", "print the ELF header and the program headers").set_defaults(func=cmd_info)

    p_sections = add("sections", "list the section headers")
    p_sections.set_defaults(func=cmd_sections)

    p_symbols = add("symbols", "dump the symbol table")
    p_symbols.add_argument("--limit", type=int, default=0, help="stop after N symbols")
    p_symbols.set_defaults(func=cmd_symbols)

    p_catalogue = add("catalogue", "write the function catalogue")
    p_catalogue.add_argument("--out", help="write a TSV file instead of stdout")
    p_catalogue.set_defaults(func=cmd_catalogue)

    args = parser.parse_args(argv)
    try:
        elf = _load(args.elf)
    except (OSError, ElfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return args.func(elf, args)


if __name__ == "__main__":
    raise SystemExit(main())
