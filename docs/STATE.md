# Where the project stands

**Date:** 2026-10-21

## What exists

| Item | State |
|---|---|
| the package is read and measured | done |
| the package reader is published, with tests | done |
| the SELF container is described | done |
| the retail executable is decrypted and rebuilt into an ELF | done, in the contributor's local workspace |
| the PPU ELF reader is published, with tests | done |
| the first function catalogue | **done**: 22,212 addresses published, four methods measured against the executable's own list ([CATALOGUE.md](CATALOGUE.md)) |
| the compiler | **identified and built**: SCEI PPC GCC 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1835 $), compiled from the published sources of the SDK 1.9.0 generation ([COMPILER.md](COMPILER.md)) |
| the first byte-exact body | **done**: `module_init` at 0x10210, 44 bytes reproduced ([src/text/module_init.c](../src/text/module_init.c)) |
| the link step | **done**: the SDK's TOC-adjusting call rule is found, measured and reproduced ([ABI.md](ABI.md)) |
| the globals | **done**: 121 TOC slots, 17,789 access sites ([GLOBALS.md](GLOBALS.md)) |
| the same engine in the next game | **done**: 721 correspondences, 73.8 % of the instructions identical ([CROSS-GAME.md](CROSS-GAME.md)) |
| the naming | the method is published; the names themselves stay in the contributor's workspace ([NAMING.md](NAMING.md)) |

## The measured facts

* The target is the USA retail release: content id
  `UP9000-NPUA80965_00-TOOLSOFDESTRUCT1`, package 16,933,424,960 bytes,
  784 entries, 15.8 GiB of game data.
* The main executable is `USRDIR/EBOOT.BIN`, 11,161,440 bytes, a retail
  SELF with key revision `0x001C` and a local NPDRM licence.
* The rebuilt executable is a 11,158,696-byte ELF64 big-endian PPU program:
  entry `0x874050`, 8 program headers, 34 section headers, an 8.34 MiB text
  segment.
* **The executable is stripped.** No symbol table, no section names, and the
  dynamic section is obfuscated. The only link information left is the
  list of modules in the dynamic string table and the module descriptor at
  the entry point.
* The compiler is the **SDK 1.9.0 generation** of Sony's PPC GCC 4.1.1,
  with RTTI: 24 objects at `$Rev: 1826 $` and 8 at `$Rev: 1830 $`. The
  published sources of that generation carry `$Rev: 1835 $` - the last of
  the line, **five revisions** after the one the bulk of the game was
  built with.

## What the measurements gave

### The compiler reproduces the retail bytes

The rebuilt compiler is not a guess: it is the toolchain of the right
family, built from its own published sources, and it reproduces the
retail bytes of a function of the target:

| Function | Address | Bytes | Flags | Result |
|---|---|---|---|---|
| `module_init` | `0x10210` | 44 | `-O1` | **match** |

`-O1` is the only level that reproduces it.  At `-O2` the candidate
differs at `0x10230`, in the epilogue: the compiler restores the stack
pointer before the link register, where the retail code does the
opposite.  The optimisation level is a property of the *file*, so it has
to be recovered file by file, exactly as the sibling project found on its
own target.

**Five revisions of the compiler did not change the code of that
function.**  The distance between `$Rev: 1835 $` and the retail's
`$Rev: 1826 $` is measurable and did not show up in the bytes.

### The `nop` after a call is a patch point

The compiler alone is 24 bytes short of the retail function.  The missing
four bytes are the delay slot of the second call, where the retail code
has `ld r2, 0x28(r1)` and the compiler leaves a `nop`.

The SDK's own header says what that `nop` is for:

```c
/* place a nop after the call so that the linker can restore the TOC
   pointer if a TOC adjusting call stub is needed.  */
```

And the retail build proves the rule, over its whole code segment:

| The delay slot of a call | the target is a stub | the target is not |
|---|---|---|
| `ld r2, 0x28(r1)` | **22,707** | 28,690 |
| `nop` | **0** | 32,044 |
| anything else | 0 | ~2,000 |

**Every** call that goes through one of the 1,037 TOC-adjusting stubs
carries the restore, and **no** call that does not, carries it.  The rule
is exact.

That is a *link* step, not a compile step, and it is the reason the
sibling project's flags (`-mno-save-restore-tocbase`, which does not
exist in this compiler) are not the answer here.  The SDK 1.9.0
generation has no such option: the restore is the linker's business.

### The TOC base and the globals

The module descriptor at the entry point names the TOC base: `0x8AB078`.
A global is a signed 16-bit displacement from it, and the measure over
the whole code segment gives **121 distinct slots** and **17,789 access
sites**, in **8,732 functions**.

The same measure on the next game gives 119 slots and 14,846 sites, and
**the same slots in the same order with almost the same counts**: the
engine's global layout survived the recompilation, even though the code
around it did not.

### The link register

Over the 9,205 functions where both the prologue and the epilogue are
identified, the link register is in `r0` in **44.4 %** of the prologues
(28.1 % in `r4`, 9.2 % in `r5`).  In the code the two games share, this
game keeps it in `r0` in 99 to 100 % of the functions - the behaviour of
the compiler rebuilt here.  The sibling project, on the newer game,
measures 28.9 % and finds the compiler it rebuilt always chooses `r0`;
that difference is what holds three of its readings a few bytes away,
and **this target does not have it**.

## What this changes

The sibling project starts from a boot executable that still carries a
symbol table, so its function boundaries and its names come for free.
Here they do not: the boundaries have to be recovered by analysis, and
every name has to be earned from the code.  That makes the *analysis* the
first real work of the project, not the compilation.

It also means the compiler question comes later than in the sibling
projects - except that on this target it does not: the compiler of the
right family is buildable from published sources, and it has already
reproduced a body byte for byte.

## The next step

1. **Qualify the link step on a second function.**  The TOC-adjusting
   call rule is measured on 22,707 calls; it has to be applied and
   verified on a body that has one.
2. **Work the catalogue from the top**: the functions whose behaviour the
   analysis makes clear, one at a time, each one ending in a comparison.
3. **Recover the link units.**  The module descriptor holds 1,748 of them,
   and the grouping decides the `nop`: a call to a function of the same
   unit is followed by no `nop`, a call to a function of another one is
   followed by one.  That is the grouping the compiler reacted to, and
   it is part of what has to be reproduced.
4. **Name the functions.**  The method is published; the names are the
   next deliverable.
5. **Extend the cross-game check**: the same source, the same options and
   the same bytes in the next game, as the sibling project did with four.
