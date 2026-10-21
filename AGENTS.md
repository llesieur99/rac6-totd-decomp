# Instructions for contributors and AI agents

Read `README.md`, `PROMPT.md`, `docs/METHOD.md`, `docs/EVIDENCE.md` and
`docs/STATE.md` before changing this project.

This repository adopts the **evidence standard and source layout** of the
sibling Ratchet & Clank decompilation projects (rac1-decomp, rac2-gc-decomp,
rac5-sm-decomp, rac-sac-decomp). It does **not** adopt their compilers, their
formats or their boundaries: the PlayStation 3 executable is a PPU program,
not a MIPS one, and the retail build is stripped.

## Ten working rules

1. **Bounds and ownership.** Each replacement range has one owner, no overlaps
   or duplicate names. A compiled prefix or a next-label interval is not proof
   of a complete function. Unknown extents remain provisional and uncounted.
2. **Explicit promotion.** Count C only when the claimed body is actually
   linked at every reviewed placement and the complete-program gates pass.
   An assembly fallback preserves the baseline but earns no C credit. One
   proven zero word of linker alignment may follow a complete body, but count
   only compiled body bytes after boundary and semantic review; promote
   separately.
3. **Evidence-based profiles.** Compiler routes, options and patches require a
   measured cause, known provenance and regression controls. Do not select a
   compiler just because one sample matches. Requalify affected accepted
   bodies.
4. **Proven names and types.** Keep reference symbols stable. Descriptive
   aliases, prototypes, field sizes, offsets and signedness need evidence from
   symbols, code, callers or data. Share definitions rather than inventing
   layouts.
5. **Bounded experiments.** Change one hypothesis at a time. After three
   attempts with the same mismatch class, recover context, change approach or
   park the best source with its first difference and a concrete reopening
   condition.
6. **Original behavior.** Preserve original behavior, including bugs, in
   matching work. Do not add purposeless C tricks to steer code generation.
   Bug fixes and PC platform adaptations belong in explicitly separate work
   and earn no matching credit. This does not relax the strict
   no-instruction-assembly rule.
7. **Public hygiene.** Keep scratch directories, probes, generated lists and
   raw reports private. Index useful alternatives by function in
   `nonmatching/`. Reusable tools belong in `tools/` with tests; public text is
   English.
8. **Pure C evidence.** C/C++ evidence must come from compiler-generated
   instructions: no inline or global assembly, no fixed-register bindings, no
   raw instruction words, no artificial assembly barriers, and no edits to
   compiler output. A file-scope assembler-name label on a declaration is
   allowed solely to name a reference symbol; it must emit no instructions.
9. **Authored form, not steered codegen.** When the compiled bytes do not
   match, the answer is the *source*, not the compiler's mood. Recover the
   authentic form of the routine: where the values live, how many are live at
   once, in which order they are produced. A construct whose only purpose is
   to move a value into a different register is not accepted.
10. **One writer in the clone.** Only the root integrates. Agents write in
    their own lot directory under `work/`.

## The PS3 specifics that replace the PS2 ones

* The executable is **stripped**. There is no symbol table and no section
  name. Every function name in this project starts as a *hypothesis* and must
  be justified by the code, its callers, or a string it references.
* The PPU is a big-endian PowerPC. The compiler is Sony's PPC GCC 4.1.1
  of the **SDK 1.9.0 generation** (`CELL 4.1.2.7, RTTI`), and it is
  **buildable from published sources** - the project's first byte-exact
  body was produced with it.
* The retail executable is **NPDRM-encrypted** and its decryption needs
  console key material. The decryption helper is private; the repository
  documents the scheme and points at RPCS3.
* The `nop` in the delay slot of a call is a **patch point for the
  linker**, not the compiler's decision: a call that goes through a
  TOC-adjusting stub carries `ld r2, 0x28(r1)` there. The link step is
  part of the proof, and it is measured (see `docs/ABI.md`).

## What counts as a match

After the applicable program layout, assembly baseline, function boundary and
compiler profile have been qualified, keep one authored C/C++ definition per
function in `src/`. A useful but nonmatching attempt belongs in
`nonmatching/`. Only a qualified toolchain reproducing the **complete retail
program bytes at every applicable placement** can establish a match.
Compiling successfully, matching a few instructions, or comparing masked bytes
cannot.

## Never commit

Disc images, packages, retail executables, extracted modules, instruction
listings, disassembly, assets, proprietary tools, build output, console keys
or licence files, SDK sources or headers, leaked or NDA source, and personal
paths. The `.gitignore` covers the common local locations, but review your own
diff: the guard is structural, not a substitute for reading the diff.

## Checks

Run the repository's own checks before a commit, and describe in the pull
request what was verified and what remains provisional. Checks enforce
structural invariants, not semantic truth: names, types, patch justification,
intent and original behavior still require evidence and review.

```
python3 tools/check_repository.py
python3 -m unittest discover -s tests -v
```

The first needs nothing but the repository; the second needs only the
standard library. The gates that measure a body again need the private
workspace and are described in `docs/GATES.md`.
