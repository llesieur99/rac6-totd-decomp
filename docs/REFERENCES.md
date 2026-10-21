# References

What the project borrows from, and what it deliberately does not.

## The other PlayStation 3 decompilations

A few projects work on PS3 executables. None of them is a matching
decompilation of a Ratchet &amp; Clank title, and each one answers a
different question, but their tooling and their write-ups are the best
available reference for the PPU.

| Project | What it does | What it gives this project |
| --- | --- | --- |
| [sp00nznet/ps3recomp](https://github.com/sp00nznet/ps3recomp) | a static recompiler: it lifts the PPU to x86 and runs the game | the architecture of a PPU recompilation pipeline, and `tools/unfself.py`, a readable SELF reader in Python that shows the container's structure |
| [andrebrumdev/gow2-recomp](https://github.com/andrebrumdev/gow2-recomp) | a recompilation of *God of War II* | `tools/decrypt_self.py`, a Python port of the retail SELF/NPDRM decryption, and a worked example of a game's PPU analysis |
| [erikomis/infamous2-recomp](https://github.com/erikomis/infamous2-recomp) | a recompilation of *inFamous 2* | `rap2rifkey.py`, another independent implementation of the licence-key derivation, and a large, well-organised road map |
| [n0madic/Soulcalibur2HD-recomp](https://github.com/n0madic/Soulcalibur2HD-recomp) | a recompilation of *Soulcalibur II HD* | the structure of a PPU port with a Vulkan/Metal backend, and the licensing notes a PS3 port needs |
| [sagemono/lv0pen](https://github.com/sagemono/lv0pen) | a byte-matching decompilation of the PS3 boot chain | the closest thing to this project's method: how a PPU program is matched, and how the compiler's output is compared |
| [pixel-stuck/ps3_lv0ldr_decomp](https://github.com/pixel-stuck/ps3_lv0ldr_decomp) | a decompilation of the PS3's own boot loaders | how the platform's own code names its functions when there are no symbols |

Two lessons are drawn from them:

* **The container is solved, the compiler is not.** The SELF/NPDRM scheme is
  documented and implemented in several languages; the PPU compiler that
  produced the retail binaries is proprietary, and every project that
  matched bytes had to bring its own.
* **The two philosophies differ, and so do their tools.** A *recompilation*
  translates the retail code and runs it; a *matching decompilation*
  rebuilds it in C and proves the bytes. This project follows the second,
  like the sibling Ratchet &amp; Clank projects do, and borrows the
  first's instrumentation ideas.

## The tools this project uses

* [RPCS3](https://github.com/RPCS3/rpcs3) — the reference implementation of
  the SELF/NPDRM decryption (`rpcs3/Crypto/unself.cpp`,
  `rpcs3/Crypto/key_vault.cpp`, `rpcs3/Crypto/unedat.cpp`). This project
  documents the scheme and points at RPCS3 rather than publishing console
  key material.
* [Ghidra](https://github.com/NationalSecurityAgency/ghidra) — the
  `PowerPC:BE:64` language reads the PPU code well enough to recover the
  function boundaries and to read the data.
* [Capstone](https://github.com/capstone-engine/capstone) — used locally to
  check the instruction patterns that the published scanner relies on. The
  published tools decode the few opcodes they need themselves, so that
  they stay dependency-free.

## The sibling Ratchet &amp; Clank projects

This project follows the method of the OpenRAC family — the evidence
standard, the source layout, the gates and the ten working rules — and
differs from it where the platform does:

| | The PS2 projects | This project |
| --- | --- | --- |
| executable | MIPS, with a symbol table | PPU, stripped |
| boundaries | given by the boot's symbols | recovered by analysis |
| names | given by the symbols | earned from the code |
| compiler | Sony's, supplied by the contributor | Sony's PPC GCC 4.1.1 of the SDK 1.9.0 generation, **built from published sources** |
| container | an ISO 9660 image | a Sony package and a SELF container |

The tools, the tests and the documentation of the sibling projects are the
model for what is published here.

## The toolchain's own sources

The compiler this project uses is built from the sources published in
[`sagemono/ps3gcc`](https://github.com/sagemono/ps3gcc), one branch per
SDK generation.  The branch of this target is
`toolchain-src-1.9.0-GCC411`, and its `gcc/gcc/version.c` is what names
the compiler:

```c
#define VERSUFFIX " (CELL 4.1.2.7, RTTI, $Rev: 1835 $)"
```

Those sources are a *build tool*, not game material: the project builds
them locally, publishes the written result, and never ships the toolchain
itself, exactly as the sibling PlayStation 2 projects do with Sony's
SN ProDG.  See [COMPILER.md](COMPILER.md).
