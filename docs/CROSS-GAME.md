# The same engine, one generation apart

*Tools of Destruction* (2008) and *A Crack in Time* (2009) are the same
studio's engine, one generation apart. That makes the older game the best
possible reference for the newer one - and the newer one the best possible
control for the older one. This document records what the two executables
say to each other.

| Game | Year | Compiler stamp |
|---|---|---|
| **Ratchet &amp; Clank Future: Tools of Destruction** | 2008 | `CELL 4.1.2.7, RTTI, $Rev: 1826 $` (24 objects), `$Rev: 1830 $` (8 objects) |
| Ratchet &amp; Clank Future: A Crack in Time | 2009 | `SDK270, $Rev: 3019 $` (106 objects), `SDK250, $Rev: 2824 $` (1) |

The sibling project
([`rac8-act-decomp`](https://github.com/llesieur99/rac8-act-decomp)) works
on the newer game. This one works on the older one, and the two share their
tooling.

## The two executables, side by side

| | Tools of Destruction | A Crack in Time |
|---|---|---|
| the code segment | `0x10000` - `0x8676E0` (8.34 MiB) | `0x10000` - `0xC19560` (12.04 MiB) |
| prologue candidates | 14,504 | 22,592 |
| call targets | 11,073 | 15,328 |
| the two cheap methods together | 4,306 | 8,271 |
| functions with a prologue and an epilogue | 9,205 | 15,535 |
| the module descriptor | 24,069 entries | 68,490 entries |
| the link register in `r0` (those functions) | **44.4 %** | 28.9 % |

The newer game has **1.44 times** the code of the older one. It is the
bigger game; it is also the one that was recompiled.

## The correspondence

Addresses mean nothing from one build to the next, so the correspondence
is made on the *shape* of the code. Three levels of proof are used, from
the strongest to the weakest:

1. **identical bytes** - the same instructions in the same order, with the
   call displacements blanked (that is the signature of
   [`tools/ppu_signature.py`](../tools/ppu_signature.py));
2. **identical shapes** - the same sequence of operations, with the
   registers and the immediates changed (the same source, another
   compiler);
3. **the call graph** - the functions one calls correspond to the
   functions the other calls.

Over the 22,592 functions of *A Crack in Time*, **721** have an
identifiable counterpart in *Tools of Destruction* (3.19 % of the newer
game, 4.97 % of the older one). The sample was 553 of the newer game's
functions, spread over the 96 blocks of 64 KiB of its code; 27 of them
(4.9 %) matched, and all 27 are functions that at least two other
functions call. That is where the engine lives.

The matches are not spread out at random. They form blocks, because whole
modules were carried over from one game to the next:

| Shared block | In A Crack in Time | In Tools of Destruction |
|---|---|---|
| the third-party library | `0x8F32E0` - `0x925F78` | `0x83F348` - `0x85FC88` |
| the engine module | `0x6DB0AC` - `0x6E6738` | `0x6EE0D0` - `0x6FCC44` |
| module 3 | `0x712978` - `0x720390` | `0x686560` - `0x6A2D90` |
| module 4 | `0x7ED470` - `0x7F9C88` | `0x77318C` - `0x78E1F8` |
| module 5 | `0x9C2CC8` - `0x9DA1D0` | `0x5DB144` - `0x5EEF24` |

## The same function, byte for byte, in both games

One pair of functions carries **the same eighty bytes** in the two
executables: this game's `float_to_short` at `0x6F0250` and the next
game's at `0x6E1C78`.

```
0x6F0250  stdu   r1, -0xa0(r1)      0x6E1C78  stdu   r1, -0xa0(r1)
0x6F0254  mflr   r0                 0x6E1C7C  mflr   r0
0x6F0258  std    r29, 0x88(r1)      0x6E1C80  std    r29, 0x88(r1)
0x6F025C  addi   r3, r1, 0x70       0x6E1C84  addi   r3, r1, 0x70
0x6F0260  stfd   f1, 0xd0(r1)       0x6E1C88  stfd   f1, 0xd0(r1)
0x6F0264  mr     r29, r4            0x6E1C8C  mr     r29, r4
0x6F0268  addi   r4, r1, 0xd0       0x6E1C90  addi   r4, r1, 0xd0
0x6F026C  std    r0, 0xb0(r1)       0x6E1C94  std    r0, 0xb0(r1)
0x6F0270  bl     0x84B3E8           0x6E1C98  bl     0x903748
0x6F0274  nop                      0x6E1C9C  nop
0x6F0278  lhz    r0, 0x70(r1)       0x6E1CA0  lhz    r0, 0x70(r1)
0x6F027C  lfd    f1, 0xd0(r1)       0x6E1CA4  lfd    f1, 0xd0(r1)
0x6F0280  extsh  r0, r0            0x6E1CA8  extsh  r0, r0
0x6F0284  stw    r0, 0(r29)        0x6E1CAC  stw    r0, 0(r29)
0x6F0288  ld     r0, 0xb0(r1)       0x6E1CB0  ld     r0, 0xb0(r1)
0x6F028C  ld     r29, 0x88(r1)      0x6E1CB4  ld     r29, 0x88(r1)
0x6F0290  addi   r1, r1, 0xa0       0x6E1CB8  addi   r1, r1, 0xa0
0x6F0294  mtlr   r0                0x6E1CBC  mtlr   r0
0x6F0298  blr                      0x6E1CC0  blr
```

Only the callee's address differs (`0x84B3E8` here, `0x903748` there).

**The same source, the same options and the same bytes in two games,
compiled by two compilers.**  That is the strongest result the two
projects have between them: it says the source form is the authentic one,
and it says the engine's shared code was not touched between the two
builds.

## The same function, twice

Twenty pairs were compared instruction by instruction. The two lots are
worth separating: in ten of them the code is **rigorously identical**, in
the other ten it was **recompiled**.

| # | A Crack in Time | Tools of Destruction | size (ACT) | size (ToD) | instructions | identical |
|---|---|---|---|---|---|---|
| 1 | `0x9BDA00` | `0x834198` | 1032 | 1032 | 258 | **258 (100 %)** |
| 2 | `0x9BD598` | `0x833D30` | 816 | 816 | 204 | **204 (100 %)** |
| 3 | `0x901D58` | `0x848238` | 464 | 464 | 116 | **116 (100 %)** |
| 4 | `0x901F28` | `0x848408` | 352 | 352 | 88 | **88 (100 %)** |
| 5 | `0x9BD8C8` | `0x834060` | 312 | 312 | 78 | **78 (100 %)** |
| 6 | `0x902088` | `0x848568` | 264 | 264 | 66 | **66 (100 %)** |
| 7 | `0x717608` | `0x810268` | 256 | 256 | 64 | **64 (100 %)** |
| 8 | `0x6E3718` | `0x6F1B00` | 184 | 176 | 44 | **44 (100 %)** |
| 9 | `0x6E1CC8` | `0x6F02A0` | 160 | 160 | 40 | **40 (100 %)** |
| 10 | `0x90B110` | `0x852ED0` | 144 | 144 | 36 | **36 (100 %)** |
| 11 | `0x71C378` | `0x813AE8` | 1840 | 1640 | 410 | 167 (41 %) |
| 12 | `0x90AED0` | `0x852908` | 576 | 576 | 144 | 133 (92 %) |
| 13 | `0x9147D8` | `0x85ADE8` | 1408 | 1408 | 352 | 346 (98 %) |
| 14 | `0x71BB40` | `0x813230` | 992 | 1000 | 248 | 93 (38 %) |
| 15 | `0x902968` | `0x849CB0` | 696 | 984 | 174 | 140 (80 %) |
| 16 | `0x71AA70` | `0x812298` | 808 | 784 | 196 | 87 (44 %) |
| 17 | `0x6E4380` | `0x6F23C0` | 496 | 496 | 124 | 118 (95 %) |
| 18 | `0x90FFA0` | `0x845248` | 704 | 696 | 174 | 78 (45 %) |
| 19 | `0x9A2E80` | `0x819088` | 880 | 960 | 220 | 68 (31 %) |
| 20 | `0x90B468` | `0x852B48` | 432 | 328 | 82 | 78 (95 %) |

**2,302 instructions out of 3,118 are identical byte for byte (73.8 %).**

The structure survives in both lots: the same frame, the same number of
calls, the same epilogue, the same sequence of operations. They are the
same sources.

The difference between the two lots is *which* build was recompiled. In
the first lot the bytes did not move at all, and in the second lot the
divergence comes early - the tenth instruction, usually - and takes the
shape of a register redistribution: the link register moves from `r0` to
`r4` or `r5`, the working registers are shuffled, and the delay slot of
one call is used where the other build has a `nop`.

**The conclusion is the one that matters for this project: it is *A Crack
in Time* that was recompiled** (against the SDK 2.7.0), not *Tools of
Destruction*. The engine's code was carried over; the game's own code was
rebuilt.

## The engine's initialisation, in both games

The engine's initialisation function is the first function of the code
segment in *A Crack in Time*, at `0x10200`:

```
0x00010200  stdu   r1, -0x70(r1)
0x00010204  mflr   r0
0x00010208  std    r0, 0x80(r1)
0x0001020c  bl     0x10638
0x00010210  nop
0x00010214  bl     0x4e2518
0x00010218  nop
0x0001021c  ld     r0, 0x80(r1)
0x00010220  mtlr   r0
0x00010224  addi   r1, r1, 0x70
0x00010228  blr
```

Its counterpart in *Tools of Destruction* is at `0x10210`:

```
0x00010210  stdu   r1, -0x70(r1)
0x00010214  mflr   r0
0x00010218  std    r0, 0x80(r1)
0x0001021c  bl     0x146ac
0x00010220  nop
0x00010224  bl     0x10200
0x00010228  ld     r2, 0x28(r1)      <- the TOC base, restored
0x0001022c  ld     r0, 0x80(r1)
0x00010230  mtlr   r0
0x00010234  addi   r1, r1, 0x70
0x00010238  blr
```

Same frame (`-0x70`), same link register slot (`0x80(r1)`), same two
calls, same epilogue. The only difference is the **delay slot of the
second call**: the older game uses it to restore the TOC base, the newer
one has a `nop`. The strict signature therefore fails on a 20-byte motif,
and the 20-byte motif is found in nine places in the older game - the
first of them being `0x10210`.

The two callees correspond as well:

* `ACT 0x10638` ↔ `ToD 0x146AC`: same shape (frame `0x70`, a load
  through the TOC, `cmpwi cr7`, `beq-`), the structure's offsets permuted
  and `r3`/`r4` swapped;
* `ACT 0x4E2518` ↔ `ToD 0x864598`: the same instruction sequence, the
  registration routine (`__cxa_atexit`), with only the TOC offset and one
  temporary register different.

### The 1,036 stubs

The older game registers its routines through a **table of local stubs**
that the newer game does not have at all:

```
0x00010200  std    r2, 0x28(r1)
0x00010204  addis  r2, r2, 2
0x00010208  addi   r2, r2, -0x14
0x0001020c  b      0x864598
```

Each stub saves `r2`, computes a TOC-relative address and jumps in the
tail to the real routine; the caller restores `r2` in the delay slot,
which is exactly the difference seen above.

*Tools of Destruction* stacks **1,036 such stubs**, four instructions
each, between `0x10280` and `0x14330` - 16,576 bytes of table.
*A Crack in Time* has **none**: it calls the registration routine
directly.

This is the sharpest structural difference between the two builds, and it
is the one that makes the older game a *reading* of the newer one rather
than its ancestor.

## The link register, in the shared code

The two games share large blocks of code. In those blocks, the same
source is compiled by two compilers, and the two builds do not choose the
same register for the link register:

| Shared block | A Crack in Time (SDK270) | Tools of Destruction (CELL 4.1.2.7) |
|---|---|---|
| the third-party library | `r5` 48 %, `r0` 37 %, `r6` 5 % | **`r0` 100 %** |
| the engine module | `r0` 51 %, `r5` 15 %, `r4` 13 % | **`r0` 99 %** |

The choice follows the compiler, not the source. And since the compiler
built from the published sources always chooses `r0`, **the older game is
the one whose compiler the published sources reproduce** - while the newer
one is not.

That is the reason this project starts with *Tools of Destruction*: the
register allocation is the first thing that differs when a candidate is
compared with the retail bytes, and here it is the one the rebuilt
compiler already produces. See [ABI.md](ABI.md) for the measurement and
[STATE.md](STATE.md) for what it means for the first readings.

## The globals, in both games

The globals are reached through the TOC, and the TOC base is the one the
module descriptor names: `0x8AB078` in *Tools of Destruction*,
`0xD34770` in *A Crack in Time*. A global is a signed 16-bit
displacement from that base, so the set of displacements is the set of
globals.

The measure, run identically on the two executables:

| | Tools of Destruction | A Crack in Time |
|---|---|---|
| distinct TOC slots | **121** | **119** |
| access sites | 17,789 | 14,846 |
| functions that touch one | 8,732 | 11,437 |
| negative offsets | 73.6 % | 73.9 % |

And the most used slots are the **same slots, in the same order, with
almost the same counts**:

| Slot | Tools of Destruction | A Crack in Time |
|---|---|---|
| `+0x802` | 6,884 | 7,197 |
| `-0x1EFE` | 2,920 | 899 |
| `-0x17FE` | 2,223 | 3,511 |
| `+0x9C2` | 835 | - |
| `-0x16FE` | 474 | 310 |
| `+0x902` | 378 | 235 |
| `-0x14FE` | 315 | 121 |

The engine's global layout **survived the recompilation**. The two
executables disagree on almost every instruction, and they agree on the
shape of the global table. That is a strong hint about where the
recompilation stopped: the data layout was kept, the code was not.

## How the search is done

The addresses are not the same from one game to the next, so the search
compares the *shape* of the code: the displacement of every branch is
blanked, and what is left is compared.
[`tools/ppu_signature.py`](../tools/ppu_signature.py) does this:

```sh
python tools/ppu_signature.py <reference.elf> <address> <length> \
    --search <other.elf> --search <another.elf>
```

```sh
$ python tools/ppu_signature.py act.elf 10200 44 --search tod.elf
tod.elf: not found          # the 44-byte motif does not survive
$ python tools/ppu_signature.py act.elf 10200 20 --search tod.elf
tod.elf: found at 0x10210   # the 20-byte motif does
```

The two commands are the whole method in two lines: the strict motif
fails, the shorter one succeeds, and the difference between them says
exactly what the recompilation changed.

## What the other games teach about the analysis

**The code segment cannot be recognised by its size.** The PPU executables
carry the SCE flags next to the usual permission bits, and the segment
that holds the code is *not* the largest executable segment: in
*Tools of Destruction* the largest one that carries the executable bit is
a **data** segment of 8.7 MiB of BSS at `0x10060000`. The code is the
*lowest* segment that carries a payload, and both tools use that rule.

**The prologue pattern is a property of the SDK version.** The scan is
calibrated on one SDK's shape, and it is weaker on another one:

| Game | prologue candidates | call targets | both |
|---|---|---|---|
| Tools of Destruction (SDK 1.9.0) | 14,504 | 11,073 | 4,306 |
| A Crack in Time (SDK 2.7.0) | 22,592 | 15,328 | 8,271 |
| Jak 3 (SDK 3.6.0) | 17,551 | 3,853 | 2,191 |

A catalogue built with one SDK's pattern is not a catalogue for another
SDK, and the two have to be kept apart. This project's catalogue is the
older game's, and it is **not** interchangeable with the sibling's.
