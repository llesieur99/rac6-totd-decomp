# The method

The project works in **waves**. Each wave takes a bounded slice of the
executable, produces a measured result and a written source, and ends with
a pull request that says exactly what was proven.

## The foundation lot

The foundation lot is the work that has to exist before any function can be
matched:

1. **Pin the target.** Record the package, the executable and the rebuilt
   ELF in `config/target.json`, with their sizes and hashes. A later claim
   that refers to "the executable" means this file and no other.
2. **Extract.** `tools/pkg.py` reads the package and writes the executable.
3. **Rebuild.** The SELF container is decrypted and rebuilt into the
   original ELF (see [SELF-FORMAT.md](SELF-FORMAT.md)).
4. **Map.** The program headers, the sections and the module names are
   recorded. Nothing is named yet; the map is addresses and sizes.

## The body waves

A body wave takes one function and goes through the same steps:

1. **Find the boundary.** The retail build has no symbols, so the
   boundaries come from the analysis: the prologue/epilogue pattern of the
   PPU code, the call targets, and the data the function touches. A
   boundary is a claim until the compile reproduces it.
2. **Name it.** The name comes from what the code does, from the strings it
   references, from its callers, or from the module it belongs to. A
   descriptive alias is allowed, but it is documented as an alias.
3. **Write the C.** One authored definition per function, in `src/`,
   in the order the code does its work. No assembly, no fixed registers, no
   tricks to steer the compiler.
4. **Compile, link and compare.** The candidate is compiled with the
   qualified toolchain and linked at the measured address; the **link
   step** is applied (the SDK's TOC-adjusting call rule, see
   [ABI.md](ABI.md)); then the bytes are compared with the retail bytes.
5. **Park or promote.** A body that does not match is parked in
   `nonmatching/` with its first difference and a reopening condition. A
   body that matches is promoted by the root, which re-measures it.

## The complete-program gate

The end state is a build that reproduces the **whole** retail program, byte
for byte, with the retail hash. Until the toolchain and its options are
qualified, this gate stays closed and no percentage is published: see
[GATES.md](GATES.md).

## The agent protocol

`PROMPT.md` is the starter prompt: it tells an agent what to read, what to
produce and what never to publish. Each agent works in its own lot
directory under `work/`, and only the root integrates.
