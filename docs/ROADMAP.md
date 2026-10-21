# Roadmap

The order of the work, and what each step needs. The steps are ordered by
dependency, not by appeal: nothing below is worth doing before the step
above it.

## 1. The container (done)

Read the package, describe the SELF container, rebuild the executable.
Tools: `tools/pkg.py`, `tools/ppu_elf.py`. Documentation:
[PKG-FORMAT.md](PKG-FORMAT.md), [SELF-FORMAT.md](SELF-FORMAT.md),
[PPU-EXECUTABLE.md](PPU-EXECUTABLE.md).

## 2. The function catalogue (done)

The module descriptor, the prologue scan, the call scan and the flow
bounds, each measured against the executable's own list. The published
catalogue holds 22,212 addresses, with the evidence for each.
Documentation: [CATALOGUE.md](CATALOGUE.md).

What is left: the functions that follow a call that never returns, and
the cases of jump tables that are written in memory rather than inline.
Both are known, bounded and measured in the sibling project on the same
kind of executable.

## 3. The naming (method done, names open)

* Attach the strings, the data and the module each function touches, so
  that a name can be justified instead of guessed.
* Keep the aliases explicit: a descriptive name is a name with a stated
  reason, not a fact.
* Needs: step 2, which is done.

## 4. The first sources (started)

* Write the first C sources for the functions whose behaviour the analysis
  makes clear, one file per function, in `src/`.
* Record what each source proves and what it does not.
* The first one is done: `module_init` at 0x10210, 44 bytes reproduced.
* Needs: steps 2 and 3.

## 5. The compiler (done)

* The compiler is identified: Sony's PPC GCC 4.1.1 of the SDK 1.9.0
  generation, and it is **built** from its published sources.
* It is qualified on one function: the source form and the options that
  reproduce the retail bytes are measured, and they are `-O1`.
* The **link step** is identified and measured too: the TOC-adjusting
  call rule is the linker's, not the compiler's.
* What is left: the link layout - the segment order, the alignment, the
  relocation rules, the stub table - and the other revision of the
  compiler (`$Rev: 1830 $`).

## 6. The gates (the body gate is open)

* The body gate is open for the functions listed in `src/`.
* The placement gate and the complete-program gate stay closed until the
  link layout is qualified.
* Only then publish counts, and only then a percentage.
* Needs: step 5.

## 7. The native port

* Once the program matches, the same approach the sibling projects use
  applies: run the game's own code on a PC, with a renderer, a sound
  backend and the game's own data.
* Needs: step 6.
