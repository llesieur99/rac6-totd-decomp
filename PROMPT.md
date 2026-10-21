# PROMPT

This is the starter prompt: what an agent reads before it touches the
project, and the prompt to launch a wave.

## Before you start

Read, in this order:

1. `README.md` - what the project is and what it holds.
2. `AGENTS.md` - the ten working rules, and what must never be committed.
3. `docs/METHOD.md` - the wave protocol.
4. `docs/EVIDENCE.md` - what counts as a proof.
5. `docs/GATES.md` - the three gates.
6. `docs/STATE.md` - where the project stands, and what the next step is.

Then read `docs/ROADMAP.md` and pick the step that is not done.

## The prompt to launch a wave

```
You are working on the Ratchet & Clank Future: Tools of Destruction
matching decompilation (PlayStation 3, USA, NPUA80965). The repository is
at <path>. The local workspace, with the package, the decrypted executable
and the analysis projects, is at <path>/work.

Read README.md, AGENTS.md, docs/METHOD.md, docs/EVIDENCE.md and
docs/STATE.md first.

Your lot is <lot>: the functions or the area you own. Work only in
work/lots/<lot>/. Do not edit src/ or config/ - the root integrates.

For each function in your lot:

  1. establish the boundary and write down the evidence;
  2. establish the name and write down the reason;
  3. write the C source, one definition per function, in the order the
     code does its work;
  4. compile it with the qualified toolchain, link it at the measured
     address, apply the SDK's TOC-adjusting call rule, and compare every
     byte with the retail bytes;
  5. if it matches, describe what you compared and how to reproduce it;
     if it does not, park the source with its first difference and a
     concrete reopening condition.

Never commit: packages, executables, extracted modules, disassembly,
instruction listings, assets, console keys, licence files, proprietary
toolchains, SDK sources, leaked or NDA source, or personal paths. The
repository publishes written source, tools, measurements and documentation.

When you are done, open a pull request that says: the target identity, the
method, the evidence, the uncertainty, and the exact commands that
reproduce your results.
```

## The short version

* One function per file, in `src/`, in the order the code works.
* The proof is the bytes, not the intention.
* The link step is part of the proof: a call to a TOC-adjusting stub
  carries `ld r2, 0x28(r1)` in its delay slot, and the compiler leaves a
  `nop` there.
* A name is earned, or it is an alias and it says so.
* Nothing game-derived leaves the workspace.
