# Contributing

Thanks for helping. This project is small and strict on purpose: a claim is
worth only what its evidence proves.

## Before you start

1. Read `README.md`, `AGENTS.md` and `docs/METHOD.md`.
2. Check the open issues and the roadmap (`docs/ROADMAP.md`) so that two
   people do not work on the same function.
3. State your scope in an issue before a substantial piece of work, and
   reserve the functions you intend to take there.

## What you need

* Python **3.12 or newer** for the tools and the tests. The published tools
  use only the standard library.
* **Your own lawful copy** of the game. The project cannot supply the
  package, the executable or the licence file.
* For the analysis step, a disassembler that understands big-endian
  PowerPC. Ghidra's `PowerPC:BE:64` language reads the PPU code well enough
  to recover function boundaries.

## How to contribute

1. Fork this repository, clone your fork, and create a branch from the
   current `master`:

   ```sh
   git clone https://github.com/YOUR-USERNAME/rac6-totd-decomp.git
   cd rac6-totd-decomp
   git remote add upstream https://github.com/llesieur99/rac6-totd-decomp.git
   git fetch upstream
   git switch master
   git merge --ff-only upstream/master
   git switch -c research/topic
   ```

2. Run the same checks as CI:

   ```sh
   python -m unittest discover -s tests -v
   python tools/check_repository.py
   ```

3. Make one focused, reviewable change. Keep the game-derived material in
   your own local workspace; only the written result belongs in the pull
   request. Record the target identity, the method, the evidence, the
   uncertainty, and the exact validation commands in the pull request.
4. Run the tests again, review `git diff` and the staged files for private
   material, then push your branch and open a pull request against `master`.

## Naming and style

* Public text is English. Comments in C/C++ are English too.
* One authored C/C++ definition per function, in `src/`, named after the
  behaviour the code proves, not after a guess.
* Tools live in `tools/` and come with tests in `tests/` that run on
  synthetic data only.
* Commits follow Conventional Commits (`feat(eboot): ...`).

## What is never published

Packages, executables, extracted modules, disassembly, instruction listings,
assets, console keys, licence files, proprietary toolchains, SDK sources,
leaked or NDA source, and personal paths. `tools/check_repository.py` is a
structural guard, not a substitute for reading your own diff.

See `LEGAL.md` for the distribution boundary.
