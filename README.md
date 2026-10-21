# Ratchet &amp; Clank Future: Tools of Destruction - matching decompilation

An early matching-decompilation workspace for **Ratchet &amp; Clank Future:
Tools of Destruction** on the PlayStation 3 (USA release, `NPUA80965`,
content id `UP9000-NPUA80965_00-TOOLSOFDESTRUCT1`).

The goal is to rebuild the retail program in **C/C++ compiled**, with a proof:
the bytes the qualified toolchain produces must be **identical** to the retail
bytes, at every applicable placement, and the complete program must still hash
to the pinned retail hash.

This repository holds the **method, the rules, the templates and the tooling**,
and the first measured results. It publishes no game code, no assets and no
console keys.

It is the sibling of
[`rac8-act-decomp`](https://github.com/llesieur99/rac8-act-decomp) (A Crack in
Time): the same evidence standard, the same layout, the same tools - and a
different, *older* target.

## What is established

The pinned USA package has been read and measured:

| Fact | Value |
|---|---|
| Content id | `UP9000-NPUA80965_00-TOOLSOFDESTRUCT1` |
| Package size | 16,933,424,960 bytes (15.8 GiB) |
| Package entries | 784 (564 files, 220 directories) |
| Main executable | `USRDIR/EBOOT.BIN`, 11,161,440 bytes |
| Executable kind | retail SELF (key revision `0x001C`, NPDRM, local licence) |
| PPU ELF | ELF64, big-endian, 8 program headers, 34 section headers |
| Entry point | `0x874050` (the module descriptor) |
| Text segment | `0x10000`, 8,746,720 bytes |
| Symbol table | **none** - the retail executable is stripped |

The container, the SELF header and the PPU ELF are all described in
[docs/](docs/): [PKG-FORMAT.md](docs/PKG-FORMAT.md),
[SELF-FORMAT.md](docs/SELF-FORMAT.md), [PPU-EXECUTABLE.md](docs/PPU-EXECUTABLE.md).

Two facts shape the whole project:

1. **The retail executable is stripped.** There is no `.symtab`, no section
   names, and the dynamic section is obfuscated. Function boundaries and names
   have to be recovered by analysis, and every name in this project is a
   hypothesis until the code proves it.
2. **The executable is NPDRM-encrypted.** The package reader
   ([tools/pkg.py](tools/pkg.py)) is published; the SELF decryption needs the
   console key material, so it stays in the contributor's local workspace.
   [docs/SELF-FORMAT.md](docs/SELF-FORMAT.md) documents the scheme and points
   at RPCS3, which does the same thing.

## Why this game, and why now

Three measurements make *Tools of Destruction* a good first target of the
series, and the first two are the reason this repository exists:

* **Its compiler is identified, and it is the older one.** The retail build
  carries two stamps of the *SDK 1.9.0* generation of Sony's PPC GCC 4.1.1 -
  `CELL 4.1.2.7, RTTI`, revisions `1826` (24 objects) and `1830` (8 objects)
  - while the sibling project works on a program built with `SDK270 rev 3019`.
  The sources of the 1.9.0 generation are published, and the last revision of
  that line (`1835`) is only five revisions away from the one the game used.
  See [COMPILER.md](docs/COMPILER.md).
* **Its register allocation is the one the rebuilt compiler produces.** In the
  code the two games share, *Tools of Destruction* keeps the link register in
  `r0` in 99 to 100 % of the functions, exactly as the rebuilt toolchain
  does, while *A Crack in Time* spreads it over `r0`, `r4`, `r5` and `r6`.
  That single difference is what holds three of the sibling project's readings
  a few bytes away. See [ABI.md](docs/ABI.md) and
  [CROSS-GAME.md](docs/CROSS-GAME.md).
* **It is a reading of the next game's engine.** 721 of the older game's
  functions have an identifiable counterpart here, and 10 of the 20 pairs
  compared instruction by instruction are **byte for byte identical**. The
  engine's code survived the recompilation; the game's own code did not.
  See [CROSS-GAME.md](docs/CROSS-GAME.md).

## Start here

| Document | What it gives you |
| --- | --- |
| [PROMPT.md](PROMPT.md) | the starter prompt - what an agent reads, and the prompt to launch a wave |
| [AGENTS.md](AGENTS.md) | the ten working rules, and what must never be committed |
| [docs/METHOD.md](docs/METHOD.md) | the wave protocol, from the foundation lot to the pull request |
| [docs/EVIDENCE.md](docs/EVIDENCE.md) | what counts as a proof, and what does not |
| [docs/GATES.md](docs/GATES.md) | the gates: the body gate, the placement gate, the complete-program gate |
| [docs/CATALOGUE.md](docs/CATALOGUE.md) | the function catalogue: how the boundaries are recovered, and on what evidence |
| [docs/COMPILER.md](docs/COMPILER.md) | the compiler, its two revisions, and how to rebuild it |
| [docs/ABI.md](docs/ABI.md) | the Cell OS Lv-2 ABI as the code shows it: frames, the TOC, the nop after a call |
| [docs/CROSS-GAME.md](docs/CROSS-GAME.md) | the same engine in *A Crack in Time*, and what the two builds teach |
| [docs/STATE.md](docs/STATE.md) | the anchor: where the project stands, and what to do next |
| [docs/ROADMAP.md](docs/ROADMAP.md) | the ordered work, and what each step needs |

## Layout

| Path | Role |
| --- | --- |
| `src/` | accepted authored C/C++ definitions, one per function |
| `nonmatching/` | useful but nonmatching attempts, indexed by function |
| `tools/` | reusable tools, with tests |
| `tests/` | the unit tests of the tools, on synthetic data only |
| `config/` | pinned metadata: target identity, measured tables |
| `docs/` | the method, the evidence standard, the anchor |
| `work/` | the private workspace: package, extracted files, analysis projects (git-ignored) |

## Using the tools

The package reader needs nothing but the Python standard library:

```sh
python tools/pkg.py inspect  "path/to/package.pkg"
python tools/pkg.py list     "path/to/package.pkg" --pattern EBOOT
python tools/pkg.py extract  "path/to/package.pkg" --out work/pkg --only EBOOT.BIN
python tools/pkg.py verify   "path/to/package.pkg" --entries
```

The PPU ELF reader works on a decrypted executable:

```sh
python tools/ppu_elf.py info     work/eboot/EBOOT.elf
python tools/ppu_elf.py sections work/eboot/EBOOT.elf
python tools/ppu_elf.py symbols  work/eboot/EBOOT.elf
```

## Public boundary

This repository publishes **written** source, reusable tools, research
metadata (names, addresses, hashes) and documentation. It never publishes
disc images, retail executables, extracted modules, instruction listings,
disassembly, assets, proprietary toolchains, console keys, SDK sources, or
leaked or NDA source. See [AGENTS.md](AGENTS.md) and [LEGAL.md](LEGAL.md).

Obtain your own lawful copy of the game; the project cannot supply one, and
the local tooling and receipts stay on your machine.

## Licence

The independently authored material here is GPL-3.0, like the sibling
projects; see [LICENSE](LICENSE). That licence does not cover the game, its
assets, any console key material or any proprietary toolchain. Contributions
should be original or compatible with that licence, with attribution where
required.

Ratchet &amp; Clank is a trademark of Sony Interactive Entertainment; the game
was developed by Insomniac Games. This is an unofficial fan project, not
affiliated with or endorsed by either.
