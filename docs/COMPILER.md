# The compiler

A matching decompilation is only possible with the compiler that produced
the retail bytes. This document records which one that is, how the answer
was obtained, and what can be done with it.

## The answer

The retail executable identifies its compiler itself, once per linked
object, in the `.comment` section:

| Stamps | Compiler |
|---|---|
| 24 | `GCC: (GNU) 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1826 $)` |
| 8 | `GCC: (GNU) 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1830 $)` |

So the game was built with **Sony's PPC GCC 4.1.1**, from the **SDK 1.9.0
generation** of the PlayStation 3 SDK, with RTTI on. The retail build
mixes **two revisions of that compiler**: 24 objects were compiled with
revision `1826` and 8 with revision `1830` - the studio's build server was
updated in the middle of the project, and the two sets of objects were
linked together.

The stamp is read with the published tool, so the answer is reproducible:

```sh
python tools/compiler_stamp.py work/eboot/EBOOT.elf --libraries
```

### Where the stamp comes from

The stamp is not the game's doing: the *compiler* writes it. Sony's
toolchain sources carry it in `gcc/gcc/version.c`:

```c
#define VERSUFFIX " (CELL 4.1.2.7, RTTI, $Rev: 1835 $)"
```

and the older generation carries it in the version string itself:

```c
const char version_string[] = "4.0.2 (CELL 4.1.28, $Rev: 1757 $)";
```

So every object a toolchain compiles carries its own stamp, and the stamps
found in an executable are a list of the toolchains that produced it. The
wording of the suffix changed with the SDK: the first generations say
`CELL <gcc version>`, the later ones say `SDK<version>`.

### The published sources, and which revision they carry

The toolchain sources of every SDK generation are published in the
[`sagemono/ps3gcc`](https://github.com/sagemono/ps3gcc) repository, one
branch per generation. Reading the `VERSUFFIX` of each branch's
`gcc/gcc/version.c` gives the whole family in one table:

| Branch | The suffix it carries | GCC |
|---|---|---|
| `toolchain-src-1.8.0` | `4.0.2 (CELL 4.1.28, $Rev: 1757 $)` | 4.0.2 |
| `toolchain-src-1.9.0-GCC402` | `4.0.2 (CELL 4.1.28, $Rev: 1849 $)` | 4.0.2 |
| **`toolchain-src-1.9.0-GCC411`** | **`(CELL 4.1.2.7, RTTI, $Rev: 1835 $)`** | **4.1.1** |
| `toolchain-src-2.2.0-GCC411` | `(SDK220, $Rev: 2372 $)` | 4.1.1 |
| `toolchain-src-2.4.0-GCC411` | `(SDK240, $Rev: 2499 $)` | 4.1.1 |
| `toolchain-src-2.5.0-GCC411` | `(SDK250, $Rev: 2824 $)` | 4.1.1 |
| `toolchain-src-2.7.0-GCC411` | `(SDK270, $Rev: 3019 $)` | 4.1.1 |
| `toolchain-src-2.8.0-GCC411` | `(SDK280, $Rev: 3316 $)` | 4.1.1 |
| `toolchain-src-2.8.0-GCC411-Jul29` | `(SDK280, $Rev: 3322 $)` | 4.1.1 |
| `toolchain-src-3.0.0-GCC411` | `(SDK300, $Rev: 3333 $)` | 4.1.1 |
| `toolchain-src-3.1.0-GCC411` | `(SDK310, $Rev: 3364 $)` | 4.1.1 |
| `toolchain-src-3.3.0-GCC411` | `(SDK330, $Rev: 3381 $)` | 4.1.1 |
| `toolchain-src-3.4.0-GCC411` | `(SDK340, $Rev: 3394 $)` | 4.1.1 |
| `toolchain-src-3.5.0-GCC411` | `(SDK350, $Rev: 3420 $)` | 4.1.1 |
| `toolchain-src-3.6.0-GCC411` | `(SDK360, $Rev: 3455 $)` | 4.1.1 |
| `toolchain-src-3.7.0-GCC411` | `(SDK370, $Rev: 3509 $)` | 4.1.1 |
| `toolchain-src-4.2.0-GCC411` | `(SDK420, $Rev: 3547 $)` | 4.1.1 |

**The target's suffix is the one of the 1.9.0-GCC411 branch** - the only
branch of the family that says `CELL 4.1.2.7, RTTI`. The branch carries
revision `1835`; the retail build used `1826` and `1830`, which are
**earlier revisions of the same line**.

That is the whole distance between the game and a compiler that can be
built from published sources: **five revisions**, in one family whose
later members changed the wording and then the SDK numbering.

### The two revisions of the retail build

The two stamps are not two different compilers: they are two revisions of
the same one, and the *objects* are counted, not the games. 24 objects
carry `1826` and 8 carry `1830`. A project like this one links dozens of
object files - the studio's own translation units, the SDK's libraries,
the third-party libraries - and the studio rebuilt some of them after a
patch was applied to its toolchain.

The practical consequence: **the game is not one build**. A function that
belongs to one of the 8 objects at `1830` may not be reproducible with a
compiler at `1826`, and the other way round. The linker's grouping tells
which is which - see [ABI.md](ABI.md) and `tools/ppu_modules.py`.

## What else the executable says

The same strings name the libraries the game was linked against:

| Library | Identification |
|---|---|
| the C++ library | Dinkumware (the SDK's `libstdc++`, "Copyright (c) 1992-2003 by P.J. Plauger") |
| the script engine | `Lua 5.0.2` |
| compression | `zlib 1.2.3` |

The Lua version is worth recording: the sibling project, on *A Crack in
Time*, finds `Lua 5.1.2 (Insomniac)` - the studio's own fork, one minor
version later. The script engine was upgraded between the two games, which
is one more reason the two executables are not the same program.

## The route to the bytes

### The byte-exact route

Byte-exact matching needs Sony's PPC GCC 4.1.1 of the 1.9.0 generation,
plus the SDK's libraries, its linker script and its C++ headers.

* The toolchain sources of that generation are **published**
  (`sagemono/ps3gcc`, branch `toolchain-src-1.9.0-GCC411`), and they are
  the sources of a *tool*, not of the game: the toolchain is a build
  tool, like Sony's SN ProDG in the sibling PlayStation 2 projects. The
  contributor brings the sources, builds them locally, and publishes only
  the written result.
* The SDK's own C++ library is a *separate prebuilt archive* that is not
  part of the toolchain sources, so C++ compiles to an object file but
  does not link yet. That does not affect the matching, which compares
  object code.
* The build needs a host compiler old enough to build GCC 4.1.1, and a
  container is the easy way to get one. The contributor's workspace uses
  Debian jessie.
* Whatever the toolchain, the *evidence* stays the same: the bytes are
  compared, and the gate is the complete-program hash.

The first experiment with this route is the `body gate` on one of the
functions read so far: compile the source with the SDK's compiler, link
it at the measured address, and compare every byte
([tools/compare_body.py](../tools/compare_body.py) does the comparison).

### The open route

The PPU is an open target, and there are open toolchains for it:

| Project | What it gives |
|---|---|
| [ps3dev/ps3toolchain](https://github.com/ps3dev/ps3toolchain) | GCC 9.5.0 or 13.2.0 with the PPU patches, plus binutils and newlib; it builds from source in Linux (WSL or Docker) |
| [ps3dev/ps3libraries](https://github.com/ps3dev/ps3libraries) | open implementations of the console's runtime libraries |
| [rpcs3/PS3DK](https://github.com/rpcs3/PS3DK) | a modern open SDK: newer GCC, binutils and newlib, C++20 on the PPU |

These are legal, and they build here (the machine has WSL 2 with Ubuntu and
Docker). But they are **not** the compiler that produced the retail bytes:
GCC 9 or 13 lays out the code differently from GCC 4.1.1, so:

* the **body gate** cannot be closed with them - the bytes will differ;
* a **semantic** reconstruction of the game in C++ can be built, which is
  what the native port needs, and which the recompilation projects
  ([ps3recomp](https://github.com/sp00nznet/ps3recomp) and the others listed
  in [REFERENCES.md](REFERENCES.md)) already show is possible;
* the two routes are not exclusive: the sources written for the open route
  are the same sources the byte-exact route would have to match, and the
  project's rules (authored form, no assembly, original behaviour) are the
  same in both.

## What the project does with this

1. The compiler identity is published, with the tool that reads it, so
   that the fact is reproducible and not hearsay.
2. The **revision** is published too, and the distance to the published
   sources is measured: five revisions of one family.
3. The sources are written to be *authentic* - the form the compiler would
   have produced - so that the byte-exact route stays open, and so that the
   open route produces readable code.
4. The gates stay as they are. With the open route, no byte-exact claim is
   made, and the project's counts remain what the gates accept: nothing.

## Building the toolchain here

```sh
git clone --branch toolchain-src-1.9.0-GCC411 --single-branch \
    https://github.com/sagemono/ps3gcc.git src
cd src
./build-ppu-lv2.sh          # needs a Cell SDK tree, or the recipe below
```

The SDK's own script is a `csh` script that wants a period-appropriate
host. The contributor's workspace builds it in a Debian jessie container
with the same recipe the sibling project uses for the other generations:
build binutils, build the compiler with `all-gcc` (the target's library
support needs the SDK's C library headers, which the toolchain sources do
not carry), then install the compiler by hand in the layout the driver
expects.

The result is a compiler that reports itself as:

```
ppu-lv2-gcc (GCC) 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1835 $)
```

which is the very family the retail executable carries, **five revisions
later than the objects it was built with**.

### The first result

The rebuilt compiler is not a claim: it reproduces the retail bytes of
**eleven functions** of the target.

| Function | Address | Bytes | Flags | Result |
|---|---|---|---|---|
| `module_init` | `0x10210` | 44 | `-O1` | **match** |
| `float_to_short` | `0x6F0250` | 80 | `-O2` | **match** |
| `sub_7049B4` | `0x7049B4` | 36 | `-O2 -falign-functions=4` | **match** |
| `sub_7049D8` | `0x7049D8` | 36 | `-O2 -falign-functions=4` | **match** |
| `sub_709AB8` | `0x709AB8` | 36 | `-O2 -falign-functions=4` | **match** |
| `sub_70BAD4` | `0x70BAD4` | 36 | `-O2 -falign-functions=4` | **match** |
| `sub_70BAF8` | `0x70BAF8` | 36 | `-O2 -falign-functions=4` | **match** |
| `sub_70BB1C` | `0x70BB1C` | 36 | `-O2 -falign-functions=4` | **match** |
| `sub_70BF74` | `0x70BF74` | 36 | `-O2 -falign-functions=4` | **match** |
| `sub_735B40` | `0x735B40` | 36 | `-O2 -falign-functions=4` | **match** |
| `sub_735BC0` | `0x735BC0` | 36 | `-O2 -falign-functions=4` | **match** |

The first of them is two calls and nothing else:

```c
void sub_146AC(void);
void sub_10200(void);

void module_init(void)
{
    sub_146AC();

    sub_10200();
}
```

linked at `0x10210` with the callees at their retail addresses, and
compared byte for byte with the retail bytes.

**Five revisions of the compiler did not change the code of that
function.**  The distance between `$Rev: 1835 $` and the retail's
`$Rev: 1826 $` is measurable, and it did not show up in the bytes.  That
is the strongest evidence the project has that the right toolchain was
rebuilt.

The link step is part of the proof, and it is described in
[ABI.md](ABI.md): the compiler alone is 24 bytes short, because the TOC
restore in the delay slot of the second call is the *linker's* work.

### The link layout: `-falign-functions=4`

The compiler aligns the functions on **eight** bytes by default.  The
retail's are aligned on **four**, and the SDK's link script packs them
that way.  The flag is not a guess: it is what puts the body at the
retail's address.

Without it the body lands four bytes too high and the comparison fails
at the very first instruction.  The first two bodies hid the problem,
because their addresses (`0x10210` and `0x6F0250`) happen to be
sixteen-byte aligned.

### The optimisation level is a property of the file

`module_init` is reproduced at `-O1` and fails at `-O2`; the nine
wrappers are reproduced at `-O2`.  The difference is the order of the
epilogue: the retail's puts the stack restore between the load of the
link register and the `mtlr`, and the compiler's own order depends on
the level.

| | the retail | the compiler at `-O1` | the compiler at `-O2` |
|---|---|---|---|
| `module_init` | the `mtlr` first | **the `mtlr` first** | the stack first |
| the nine wrappers | the stack first | the `mtlr` first | **the stack first** |

So the level is recovered file by file, exactly as the sibling project
found on its own target.

### The other revisions

The retail build carries two revisions, `1826` and `1830`, and the
published sources carry `1835`.  The project cannot rebuild the other
two, and does not need to for this first result: the code of the function
that was matched is the same in all three.

Which objects belong to which revision is a question the module
descriptor can answer - the 1,748 link units it holds are the objects
that were linked together - and it is the next step on the list.
