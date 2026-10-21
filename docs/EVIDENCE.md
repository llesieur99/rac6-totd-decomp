# Evidence

What counts as a proof, and what does not.

## Proofs

* **The bytes match.** A compiled body linked at the measured address
  produces exactly the retail bytes of the function's range, and the
  comparison is run over the whole range.
* **The hash matches.** A complete build reproduces the pinned retail hash
  of the executable.
* **A measurement is reproducible.** Anyone with the same target and the
  same tool runs the same command and gets the same number, from the
  repository's own tooling.
* **A name is earned.** The code, the callers, the data it touches or the
  module it belongs to justify the name; the write-up says which.

## Not proofs

* "It compiles."
* "The first N instructions match."
* "The disassembly looks like the source."
* "The masked bytes match" (masking hides exactly the differences that
  matter).
* "The compiler produced the same code with a different source" — that is a
  coincidence, not a match, unless the source is the authentic form.
* A function boundary derived from a next-label interval: it is a candidate
  bound, not a function.
* A name guessed from the game's documentation.

## How a claim is written

Every claim in a pull request says:

1. the target identity (the file, its hash, the address range);
2. the method (the tool, the command, the options);
3. the evidence (the bytes compared, the first difference if any);
4. the uncertainty (what is still a hypothesis);
5. the exact commands that reproduce it.

## Numbers

No percentage is published until the complete-program gate passes. Counts
are published only for what the gates accept, and a count never mixes
different scopes: a body count, a placement count and a byte count are
three different numbers and are never added together.
