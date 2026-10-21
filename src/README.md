# src

The accepted authored C/C++ definitions, one per function.

A function reaches this directory after the body gate and the placement
gate pass, and it carries the proof of its own claim: the target, the
address, the extent, the compiler, the flags, the exact commands that
reproduce the comparison, and what is still a hypothesis.

| File | Function | Address | Bytes | Result |
|---|---|---|---|---|
| [`text/module_init.c`](text/module_init.c) | the engine's initialisation | `0x10210` | 44 | **byte-exact** |
| [`text/float_to_short_6f0250.c`](text/float_to_short_6f0250.c) | a floating point conversion | `0x6F0250` | 80 | **byte-exact** |
| [`text/sub_7049B4.c`](text/sub_7049B4.c) | a wrapper | `0x7049B4` | 36 | **byte-exact** |
| [`text/sub_7049D8.c`](text/sub_7049D8.c) | a wrapper | `0x7049D8` | 36 | **byte-exact** |
| [`text/sub_709AB8.c`](text/sub_709AB8.c) | a wrapper | `0x709AB8` | 36 | **byte-exact** |
| [`text/sub_70BAD4.c`](text/sub_70BAD4.c) | a wrapper | `0x70BAD4` | 36 | **byte-exact** |
| [`text/sub_70BAF8.c`](text/sub_70BAF8.c) | a wrapper | `0x70BAF8` | 36 | **byte-exact** |
| [`text/sub_70BB1C.c`](text/sub_70BB1C.c) | a wrapper | `0x70BB1C` | 36 | **byte-exact** |
| [`text/sub_70BF74.c`](text/sub_70BF74.c) | a wrapper | `0x70BF74` | 36 | **byte-exact** |
| [`text/sub_735B40.c`](text/sub_735B40.c) | a wrapper | `0x735B40` | 36 | **byte-exact** |
| [`text/sub_735BC0.c`](text/sub_735BC0.c) | a wrapper | `0x735BC0` | 36 | **byte-exact** |

**Eleven byte-exact bodies.**  The nine wrappers came from one wave: the
recipe - the compiler of the right family, the optimisation level of the
file, the link rule and `-falign-functions=4` - was applied to every
small wrapper the catalogue holds.

When a file lands here it holds:

* one function, and nothing else;
* the behaviour of the retail function, including its bugs;
* the types and the names the evidence supports, with the alias marked as
  an alias;
* no assembly, no inline assembly, no fixed-register bindings, no raw
  instruction words.

The layout follows the executable's own structure: the area a function
belongs to becomes a directory, and the file is named after the function.
