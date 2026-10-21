# The PPU executable

The PlayStation 3's main processor is the **PPU**: a big-endian PowerPC core
with an SPU coprocessor and an RSX graphics unit. The executable of a PS3
game is a PPU program: a 64-bit big-endian ELF with a few SCE extensions.

This document records what the reader in
[`tools/ppu_elf.py`](../tools/ppu_elf.py) measures on the pinned target.

## The ELF header

| Field | Value on the target |
|---|---|
| class | ELF64 |
| endianness | big |
| `e_ident[EI_OSABI]` | `0x66` (LV2) |
| `e_type` | `2` (executable) |
| `e_machine` | `0x15` |
| `e_entry` | `0x874050` |
| `e_phoff` | `0x40` |
| `e_shoff` | `0xAA3C28` |
| `e_flags` | `0x0` |
| `e_ehsize` | 64 |
| `e_phentsize` | 56 |
| `e_phnum` | 8 |
| `e_shentsize` | 64 |
| `e_shnum` | 34 |
| `e_shstrndx` | 33 |

The program headers are the usual ELF64 ones (56 bytes) with the SCE flag
bits added to `p_flags`:

| Bit | Meaning |
|---|---|
| `0x00100000` | the segment is for the SPU |
| `0x00200000` | the segment is writable by the SPU |
| `0x00400000` | the segment is readable by the SPU |
| `0x01000000` | the segment is for the RSX |
| `0x02000000` | the segment is writable by the RSX |
| `0x04000000` | the segment is readable by the RSX |

The two last program headers are not segments at all: type `0x60000001` is
the SCE dynamic section and type `0x60000002` the SCE segment symbols, both
pointing into the data segment.

## The segments

| # | vaddr | filesz | memsz | flags | role |
|---|---|---|---|---|---|
| 0 | `0x10000` | `0x8576E0` | `0x8576E0` | `R-X` | the code |
| 1 | `0x870000` | `0x59A18` | `0x59A18` | `RW-` | the data (the descriptor, the globals, the strings) |
| 2 | `0x10000000` | `0x5DD00` | `0x5DD00` | `SPU_R` | the SPU's code, in the PPU's address space |
| 3 | `0x10060000` | `0x16B180` | `0x848550` | `SPU_RW` | the SPU's data - **8.3 MiB of BSS** |
| 4 | `0x0` | 0 | 0 | - | the RSX's segments, empty in this build |
| 5 | `0x8C9A10` | `0x8` | `0x1F8` | `R--` | the TLS block |
| 6 | `0x867698` | `0x20` | `0x20` | - | the SCE dynamic section |
| 7 | `0x8676B8` | `0x28` | `0x28` | - | the SCE segment symbols |

**The largest executable segment is not the code.**  Segment 3 carries the
executable bit and holds 8.7 MiB of BSS; the code is the *lowest* segment
that carries a payload.  A reader that picks the biggest executable
segment scans the wrong memory here, and the tools use the rule the
sibling project established: **the code is the lowest segment with a
payload**.

## The sections

The retail executable is **stripped**, and it shows:

* there is **no symbol table**: no `.symtab`, no `.dynsym`;
* there are **no section names**: the `sh_name` fields point into the
  string table of the SCE dynamic section, so the names read back as
  fragments of module names such as `p192001libfs_stub:p192001libm`.  The
  "section names" of a PS3 eboot are an artefact, not information.

The 34 sections are therefore anonymous `PROGBITS` blocks, plus a `NOBITS`
block for the BSS.  Their roles have to be recovered from their content,
and the boundaries that matter are known:

| Section | Address | Size | Content |
|---|---|---|---|
| 1-2 | `0x10200` | 8.7 MiB | the PPU text: the engine's initialisation, the **1,036 stubs**, and the game's code |
| 22 | `0x874040` | 188 KB | the module descriptor - the entry point is 16 bytes into it |
| 23 | `0x8A3078` | 158 KB | the read-only data: the window of globals, the strings, the tables |
| 25 | `0x8C9A18` | 496 | the SCE dynamic section, obfuscated |
| 26-29 | `0x10000000` | 1.2 MiB | the SPU's own code and data |
| 30 | `0x101CB180` | 7.2 MiB | the BSS (`NOBITS`) |
| 33 | - | 336 | the SCE dynamic string table (module names) |

The dynamic string table names the modules the executable links against:
`libfs_stub`, `libm`, `libaudio_stub`, `libspurs_stub`, `liblv2_stub` and
others.  It is the only piece of link information the retail build keeps.

## What the inventory found

A full inventory of the file - sections, segments, strings, import
mechanism - was made on the target and is kept in the contributor's
workspace.  Four of its results change the way the file should be read.

**`e_entry` does not point at code.**  `0x874050` is the address of a
table of **24,069 pairs** - a function address and the constant
`0x8AB078` - kept in the data segment.  The real start of the program is
the engine's initialisation function at `0x10210`, and the first thing
before it, at `0x10200`, is one of the 1,036 local stubs.

**The code segment holds the game's own data too.**  The segment at
`0x10000` holds the code and, further in, the read-only data.  The
discriminant between code and data is the **number of prologues**, not
the density of calls: the read-only data holds no prologue at all.

**The link information is richer than the stripped file suggests.**  The
executable links a dozen PRX modules (the studio's own translation units)
besides the SCE ones, and the import mechanism can be mapped - the
descriptors, the `mtctr`/`bctr` thunks - but the *names of the imported
symbols* are compressed and cannot be recovered.

**The SPU's programs are embedded in the data.**  The segments at
`0x10000000` and `0x10060000` hold the game's own SPU module and the
SDK's, as complete ELF images with their section names intact.

## What this means for the decompilation

Without symbols, a function's name has to be *earned*: it comes from the
code, from its callers, from the strings it touches, or from the module it
belongs to. Every name in `src/` is a hypothesis until the code proves it,
and the project treats it as such (see `AGENTS.md`, rule 4).

The function boundaries are recovered by analysis, not by a table: see
`docs/METHOD.md` for the procedure and `docs/ROADMAP.md` for the order of
the work.

## Reading it

```sh
python tools/ppu_elf.py info     work/eboot/EBOOT.elf
python tools/ppu_elf.py sections work/eboot/EBOOT.elf
python tools/ppu_elf.py symbols  work/eboot/EBOOT.elf
python tools/ppu_elf.py catalogue work/eboot/EBOOT.elf --out work/eboot/functions.tsv
```

`catalogue` writes the named functions; on this target the list is empty,
which is the honest answer for a stripped executable.
