# The Cell OS Lv-2 ABI, as the code shows it

What the retail executable teaches about how the SDK's compiler lays code
out.  Every statement here was measured: either by reading the compiler's
own sources (the SDK's `gcc/config/rs6000/`) or by comparing the bytes of
a candidate with the retail ones.

## The two options that are not in the upstream GCC

The SDK adds two target options to the rs6000 backend
(`gcc/config/rs6000/lv2.opt`):

| Option | Effect |
|---|---|
| `-mno-nop-after-bl` | does not generate a `nop` after a `bl` |
| `-mno-save-restore-tocbase` | does not save or restore the TOC base (r2) |

A third one, `-mcellos-kernel`, turns both of them on and adds
`-falign-functions=1 -falign-jumps=1 -falign-labels=1 -falign-loops=1`.

The retail code keeps the `nop` after most calls **and** restores the TOC
base in some functions, so the game was built with neither option *by
default*.  Which options each *file* was built with is part of what has
to be recovered.

## The `nop` after a call depends on the callee

This is the most surprising result of the sibling project, and it holds
here too:

* a call to a function the compiler **knows** (same translation unit) is
  followed by no `nop`;
* a call to a function the compiler does **not** know is followed by a
  `nop`.

The rule is the one the PowerPC ELF ABI imposes: the caller's stack must
be 16-byte aligned when the callee starts, so a `nop` is inserted when the
callee's prologue needs it - and the compiler can only know that when the
callee is in the same translation unit.

**Consequence for the project:** the grouping of the functions into
translation units is part of what has to be recovered.  A candidate that
calls a function the compiler cannot see will not match, however good its
source is.

The executable keeps the grouping itself.  Its entry point is not code
but the **module descriptor**: a table of `(function address, TOC base)`
pairs that lists what every linked module exports, in link order.
`tools/ppu_modules.py` reads it and checks the rule against the code:

```sh
python tools/ppu_modules.py work/eboot/EBOOT.elf --check
```

```
module descriptor at 0x874050: 24069 functions
  1748 link units, the largest ones holding 1009, 933, 582, 482, 479, 475, 446, 435 functions
  3 distinct TOC bases
  call to a function of the same unit : no nop ..., nop ...
  call to a function of another unit  : no nop ..., nop ...
```

On the sibling target, 98.7 % of the calls that cross a link unit carry
the `nop`, and the calls inside a unit are the ones that do not.  The
grouping is real, and it is the grouping the compiler reacted to.

## The `nop` after a call is a patch point

This is the result that is specific to this compiler, and it is the one
that the first byte-exact body needed.

The SDK's own header says what the `nop` is for:

```c
/* _init and _fini functions are built from bits spread over many
   object files, each potentially with a different TOC pointer.  For
   that reason, place a nop after the call so that the linker can
   restore the TOC pointer if a TOC adjusting call stub is needed.  */
```

So the `nop` in the delay slot of a call is **not** alignment and **not**
a decision of the compiler: it is the slot the *linker* fills in when the
call goes through a **TOC-adjusting stub**.

A TOC-adjusting stub is four instructions:

```
std   r2, 0x28(r1)      ; save the caller's TOC base in its save slot
addis r2, r2, <high>    ; compute the other module's base
addi  r2, r2, <low>
b     <the routine>     ; tail jump
```

This target carries **1,037** of them, from `0x10200` to `0x14330`
(16,704 bytes of table).  `tools/ppu_stubs.py` finds them by their shape.

The rule is exact, and it is measured over the whole code segment
(2,186,552 words, of which 51,397 are calls):

| The delay slot of a call | the target is a stub | the target is not |
|---|---|---|
| `ld r2, 0x28(r1)` | **22,707** | 28,690 |
| `nop` | **0** | 32,044 |
| anything else | 0 | ~2,000 |

**Every** call to a stub carries the TOC restore, and **no** call that
avoids one does.  The restore reads back the value the stub saved in the
caller's TOC save slot at `0x28(r1)`.

Two consequences:

* the **compiler** is not enough.  A candidate compiled for this target is
  24 bytes short of the retail's first function until the link step is
  applied - and the link step is a *separate* pass over the linked
  program, not an edit of the compiler's output;
* the option the sibling project uses (`-mno-save-restore-tocbase`) does
  **not exist** in this compiler.  It was introduced with a later SDK.
  Here the restore is the linker's business, and the flags to qualify are
  the optimisation level alone.

## The TOC base

`r2` holds the TOC (the table of contents) in the Cell OS Lv-2 ABI.  A
function that uses globals gets its TOC pointer from the chain in the
caller's frame (`ld r2, 0x28(r1)`), and a function that calls another one
restores it afterwards, because the callee may have changed it.

That is why some retail functions end with a `ld r2, 0x28(r1)` and others
do not: it depends on whether the calls they make can change `r2`.

The compiler's own source says exactly when the restore is emitted.  The
function `uses_TOC()` walks the function's RTL looking for a
`use (unspec ... UNSPEC_TOC)`, and that use is only generated where the
function *loads the TOC base* - that is, where it references a global:

```c
/* This returns nonzero if the current function uses the TOC.  This is
   determined by the presence of (use (unspec ... UNSPEC_TOC)), which
   is generated by the ABI_V4 load_toc_* patterns.  */
```

So the restore is not a property of the calls a function makes: it is a
property of the *function*, and a function that never names a global does
not restore the TOC, whatever it calls.

**This target is the best case for that rule.**  The engine's
initialisation function restores the TOC base in the delay slot of its
second call:

```
0x10210:  stdu   r1, -0x70(r1)
          mflr   r0
          std    r0, 0x80(r1)
          bl     0x146ac
          nop
          bl     0x10200
          ld     r2, 0x28(r1)      <- the TOC base, restored
          ld     r0, 0x80(r1)
          mtlr   r0
          addi   r1, r1, 0x70
          blr
```

while the same function in the next game has a `nop` there.  The older
engine's initialisation named a global; the newer one's does not.

The option `-mno-save-restore-tocbase` removes that restore as well as the
prologue's save.  The retail executable has functions with the restore and
functions without, so **the flags are not the same everywhere**: the file
that holds one function was built with the option, and the file that holds
another was not.  Qualifying the build means qualifying it *file by file*.

## The link register's register

The SDK's prologue moves the link register into a general register before
it stores it (`mflr rX` / `std rX, offset(r1)`), and the epilogue reads it
back before `mtlr`.  Which register the prologue uses is the register
allocator's choice, and it is worth measuring, because it is where a
rebuilt compiler and a retail build most often disagree.

Measured over the functions of the catalogue where **both** the prologue
and the epilogue are identified (`python tools/ppu_lr.py <eboot.elf>`
does the measure, and the population is the same for the two games):

| | Tools of Destruction | A Crack in Time |
|---|---|---|
| functions with a prologue and an epilogue | 9,205 | 15,535 |
| `r0` in the prologue | **44.4 %** | 28.9 % |
| `r4` in the prologue | 28.1 % | 26.2 % |
| `r5` in the prologue | 9.2 % | 26.3 % |
| `r6` in the prologue | 4.9 % | 6.1 % |
| `r3` in the prologue | 3.2 % | 3.5 % |
| `r0` in the epilogue | 43.9 % | 57.6 % |

And the four combinations:

| Prologue | Epilogue | Tools of Destruction | A Crack in Time |
|---|---|---|---|
| `r0` | `r0` | 1,985 (21.6 %) | 2,503 (16.1 %) |
| `r0` | another | 2,102 (22.8 %) | 1,981 (12.8 %) |
| another | `r0` | 2,052 (22.3 %) | 6,446 (41.5 %) |
| another | another | 3,066 (33.3 %) | 4,605 (29.6 %) |

**One function in five is written the way the rebuilt compiler writes it**
- prologue in `r0`, epilogue in `r0` - and that is the population the body
gate can be run on first.

### What the two games say about the compiler

The sibling project found, in the code the two games share, that the same
source is compiled by two compilers and the two builds do not choose the
same register:

| Shared block | A Crack in Time (SDK270) | Tools of Destruction (CELL 4.1.2.7) |
|---|---|---|
| the third-party library | `r5` 48 %, `r0` 37 %, `r6` 5 % | **`r0` 100 %** |
| the engine module | `r0` 51 %, `r5` 15 %, `r4` 13 % | **`r0` 99 %** |

The compiler built from the published sources always chooses `r0` - in C
and in C++, at every optimisation level, with and without
`-mno-save-restore-tocbase`, and with the TOC options turned on and off.

**So on this target the rebuilt compiler and the retail build agree on the
choice, at least in the code the two games share.**  That is the reason
this game is the first target of the series: the register allocation is
the first thing that differs when a candidate is compared with the retail
bytes, and here it does not differ.

Over the whole executable the two are not identical - 44.4 % in `r0` is
not 100 % - but the parts that remain are the parts the *game's own* code
is made of, and the parts the two games share are the parts that were
carried over from an earlier engine.

### The compiler's own source

The epilogue says where the choice is made.  In the compiler's own source,
the link register is read back into `r0` and nowhere else:

```c
/* Get the old lr if we saved it.  */
if (info->lr_save_p && (info->lr_save_inline_p || sibcall))
  {
    ...
    emit_move_insn (gen_rtx_REG (Pmode, 0), mem);
  }
```

Every branch of the published toolchain repository carries that same line,
and the compilers built from them (2.7.0, 2.8.0, 3.6.0 and 4.2.0) all
keep the link register in `r0`.

## The frame

| Layout | Value |
|---|---|
| frame | a multiple of 0x10, reserved by the function itself |
| link register | saved in the **caller's** frame, at `0x10(r1)` of the caller's stack pointer - in the function's own frame that is `0x80(r1)` for a 0x70-byte frame |
| locals | between the stack pointer and the link register's slot |
| parameter save area | reserved when the function or one of its callees needs it |

The retail code saves the link register with `mflr` into a register and
then stores it; which register it uses is the register allocator's choice,
and it differs from function to function.

## The epilogue's two shapes

The retail code ends its functions in two ways:

```
ld r0, 0x80(r1)     ; the link register
mtlr r0
addi r1, r1, 0x70   ; the stack
blr
```

```
ld r0, 0x80(r1)
addi r1, r1, 0x70
mtlr r0
blr
```

Both occur in the same executable, so the order is a property of the
function, not of the build flags.  A candidate that always produces one of
them will match half the functions and no more.

## The stub table

This target carries a structure the next game does not have: a table of
**1,036 four-instruction stubs** between `0x10280` and `0x14330`, each of
this shape:

```
std   r2, 0x28(r1)
addis r2, r2, <high>
addi  r2, r2, <low>
b     <the real routine>
```

The stub saves the TOC base, computes a TOC-relative address and jumps in
the tail; the caller restores `r2` in the delay slot of the call.  This
is where the *TOC base* of the executable comes from: the stub's
`addis`/`addi` pair is a TOC-relative address computation, and the routine
it jumps to is the registration function (`__cxa_atexit`).

The stubs are 16,576 bytes of table, and they are the first thing a
candidate has to reproduce: they are the *calling convention* of this
build, written down.

## What this means for a wave

1. Recover the *grouping* of the functions, not only the functions: the
   translation unit changes the bytes.
2. Recover the *flags* of each group.  They are not necessarily the same
   everywhere: the prologue of one function may say the TOC base is not
   saved while another's says it is.
3. Reproduce the stub table: it is part of the program, and the calls
   that go through it are the calls the compiler could not see.
4. Compare the bytes, not the intent.  The register allocator's choices are
   part of what has to be reproduced, and they are the project's evidence.
