# src

The accepted authored C/C++ definitions, one per function.

A function reaches this directory after the body gate and the placement
gate pass, and it carries the proof of its own claim: the target, the
address, the extent, the compiler, the flags, the exact commands that
reproduce the comparison, and what is still a hypothesis.

| File | Function | Address | Bytes | Result |
|---|---|---|---|---|
| [`text/module_init.c`](text/module_init.c) | the engine's initialisation | `0x10210` | 44 | **byte-exact** |

When a file lands here it holds:

* one function, and nothing else;
* the behaviour of the retail function, including its bugs;
* the types and the names the evidence supports, with the alias marked as
  an alias;
* no assembly, no inline assembly, no fixed-register bindings, no raw
  instruction words.

The layout follows the executable's own structure: the area a function
belongs to becomes a directory, and the file is named after the function.
