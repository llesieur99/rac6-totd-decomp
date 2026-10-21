# The globals of the target

The retail executable is stripped, so the game's global variables have no
names.  They do have *places*, and the places are recoverable: the
PlayStation 3's compilers address them through a **TOC** (table of
contents) held in `r2`, and the executable keeps both the TOC and the
window of globals it points at.

This document records what was measured on the target.  The catalogue
itself, with every global, its type and its access sites, is kept in the
contributor's workspace.

## How the globals are reached

The module descriptor at the entry point names the TOC base.  On this
target:

```
entry point (module descriptor) : 0x00874050
descriptor[0] (function, module): 0x00014340 0x008AB078
descriptor[1] (the TOC base)    : 0x008AB078
```

The module descriptor is a table of 24,069 `(function address, TOC base)`
pairs, and the second word - the TOC base of the executable's own module -
is `0x008AB078`.

From then on, a global is a signed 16-bit displacement from `r2`: a
32-bit load through the TOC gives the global's address, and a load
through *that* address gives a member of the structure the global points
at.

and the window of globals is the 64 KiB around the base:

| Range | Size | Content |
|---|---|---|
| `0x00874040` - `0x008A3078` | 188 KB | the module descriptor: 24,069 entries of 8 bytes, `{function address, TOC base}` |
| `0x008A3078` - `0x008B3078` | 64 KB | the window of globals, addressed from `r2` |

The base `0x008AB078` sits at the exact middle of that 64 KB window, and
the window starts right after the descriptor: the layout is the PowerPC64
**small data** convention, with the TOC holding the base of a 64 KB window
instead of a pointer per global.

## What was counted

Every `lwz`/`lhz`/`lbz`/`ld`/`lwa`/`ldu rD, off(r2)` in the code is an
access to a global.  Running that scan over the whole text segment gives:

| Measure | Value |
|---|---|
| distinct TOC slots (the globals of the main module) | **121** |
| access sites | **17,789** |
| functions that touch one | **8,732** |
| accesses through `lwz` | 6,161 |
| through `lhz` | 4,193 |
| through `ld` | 2,956 |
| through `lwa` | 2,333 |
| through `ldu` | 1,860 |
| through `lbz` | 286 |

Most of the offsets are negative - 73.6 % - which says the pointers the
game keeps point at the *end* of an object, the way a C++ compiler lays
out a class with a base at the end.

The most used slots, with the number of accesses:

| Slot | Accesses | Note |
|---|---|---|
| `+0x802` | 6,884 | the most used slot of the game |
| `-0x1EFE` | 2,920 | |
| `-0x17FE` | 2,223 | |
| `+0x9C2` | 835 | |
| `-0x16FE` | 474 | |
| `+0x902` | 378 | |
| `-0x14FE` | 315 | |
| `-0x173E` | 276 | |
| `+0xB02` | 241 | |
| `-0x1FFE` | 228 | |

The types are deduced from the way each global is used: a `lwz` alone
means a 32-bit unsigned value, a `lbz` a byte, a `lhz` a halfword, an
access of eight bytes a 64-bit value, a use followed by `extsw` a signed
integer, and a global that is dereferenced before being used a pointer.

## The layout is the same in the next game

The same measure, run identically on *A Crack in Time*:

| | Tools of Destruction | A Crack in Time |
|---|---|---|
| distinct TOC slots | **121** | **119** |
| access sites | 17,789 | 14,846 |
| functions that touch one | 8,732 | 11,437 |
| negative offsets | 73.6 % | 73.9 % |
| the most used slot | `+0x802` (6,884) | `+0x802` (7,197) |
| the second | `-0x1EFE` (2,920) | `-0x17FE` (3,511) |

The **same slots, in the same order, with almost the same counts**.  The
engine's global layout survived the recompilation, even though the code
around it did not.  That is a strong hint about the shape of the work:
the data layout was kept, the code was rebuilt.

## The dispatch tables

Some globals hold tables of `{function pointer, TOC base}`: the address
of a function in another module and the TOC base to call it with.  They
are how the engine calls across modules without a direct link.  Locating
them and measuring their use is the next step on the list, and it is open.

## What this means for the decompilation

A global that the analysis can place is a global that can be given a
type, and a type is what makes a call's prototype recoverable.  It is
also what tells apart the two halves of a structure: the members at
negative offsets and the ones at positive offsets belong to different
objects.
