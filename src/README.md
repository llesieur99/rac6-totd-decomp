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
| [`text/sub_7049FC.c`](text/sub_7049FC.c) | a wrapper | `0x7049FC` | 44 | **byte-exact** |
| [`text/sub_709AB8.c`](text/sub_709AB8.c) | a wrapper | `0x709AB8` | 36 | **byte-exact** |
| [`text/sub_70BAD4.c`](text/sub_70BAD4.c) | a wrapper | `0x70BAD4` | 36 | **byte-exact** |
| [`text/sub_70BAF8.c`](text/sub_70BAF8.c) | a wrapper | `0x70BAF8` | 36 | **byte-exact** |
| [`text/sub_70BB1C.c`](text/sub_70BB1C.c) | a wrapper | `0x70BB1C` | 36 | **byte-exact** |
| [`text/sub_70BF74.c`](text/sub_70BF74.c) | a wrapper | `0x70BF74` | 36 | **byte-exact** |
| [`text/sub_735B40.c`](text/sub_735B40.c) | a wrapper | `0x735B40` | 36 | **byte-exact** |
| [`text/sub_735BC0.c`](text/sub_735BC0.c) | a wrapper | `0x735BC0` | 36 | **byte-exact** |
| [`text/sub_770698.c`](text/sub_770698.c) | a wrapper | `0x770698` | 36 | **byte-exact** |
| [`text/sub_7706BC.c`](text/sub_7706BC.c) | a wrapper | `0x7706BC` | 36 | **byte-exact** |
| [`text/sub_7706E0.c`](text/sub_7706E0.c) | a wrapper | `0x7706E0` | 36 | **byte-exact** |
| [`text/sub_770704.c`](text/sub_770704.c) | a wrapper | `0x770704` | 36 | **byte-exact** |
| [`text/sub_7734D8.c`](text/sub_7734D8.c) | a wrapper | `0x7734D8` | 36 | **byte-exact** |
| [`text/sub_7734FC.c`](text/sub_7734FC.c) | a wrapper | `0x7734FC` | 36 | **byte-exact** |
| [`text/sub_773520.c`](text/sub_773520.c) | a wrapper | `0x773520` | 36 | **byte-exact** |
| [`text/sub_773544.c`](text/sub_773544.c) | a wrapper | `0x773544` | 36 | **byte-exact** |
| [`text/sub_787570.c`](text/sub_787570.c) | a wrapper | `0x787570` | 36 | **byte-exact** |
| [`text/sub_787594.c`](text/sub_787594.c) | a wrapper | `0x787594` | 36 | **byte-exact** |
| [`text/sub_7875B8.c`](text/sub_7875B8.c) | a wrapper | `0x7875B8` | 36 | **byte-exact** |
| [`text/sub_7875DC.c`](text/sub_7875DC.c) | a wrapper | `0x7875DC` | 36 | **byte-exact** |
| [`text/sub_787600.c`](text/sub_787600.c) | a wrapper | `0x787600` | 36 | **byte-exact** |
| [`text/sub_787624.c`](text/sub_787624.c) | a wrapper | `0x787624` | 36 | **byte-exact** |
| [`text/sub_787648.c`](text/sub_787648.c) | a wrapper | `0x787648` | 36 | **byte-exact** |
| [`text/sub_79F654.c`](text/sub_79F654.c) | a wrapper | `0x79F654` | 36 | **byte-exact** |
| [`text/sub_79F678.c`](text/sub_79F678.c) | a wrapper | `0x79F678` | 36 | **byte-exact** |
| [`text/sub_79F69C.c`](text/sub_79F69C.c) | a wrapper | `0x79F69C` | 36 | **byte-exact** |
| [`text/sub_79F6C0.c`](text/sub_79F6C0.c) | a wrapper | `0x79F6C0` | 36 | **byte-exact** |
| [`text/sub_7C581C.c`](text/sub_7C581C.c) | a wrapper | `0x7C581C` | 36 | **byte-exact** |
| [`text/sub_7D1A7C.c`](text/sub_7D1A7C.c) | a wrapper | `0x7D1A7C` | 36 | **byte-exact** |
| [`text/sub_813788.c`](text/sub_813788.c) | a wrapper | `0x813788` | 40 | **byte-exact** |

**Thirty-four byte-exact bodies.**  The nine wrappers of the first wave
came from one recipe: the compiler of the right family, the optimisation
level of the file, the link rule and `-falign-functions=4`.  The second
wave added **twenty-three** more, and measured the two rules the first
wave had only guessed at:

* the size of the frame is the number of the callee's arguments - `0x70`
  for up to eight, `0x80` for nine, whose last argument is floating
  point;
* the order of the epilogue is the level of the file - the stack pointer
  first at `-O2`, the link register first at `-O1`.

The prototypes are inferences, and they say so: the number of arguments
is read from the frame of the caller, and the types from the body of the
routine that is called - the registers it reads are the arguments it
uses.

When a file lands here it holds:

* one function, and nothing else;
* the behaviour of the retail function, including its bugs;
* the types and the names the evidence supports, with the alias marked as
  an alias;
* no assembly, no inline assembly, no fixed-register bindings, no raw
  instruction words.

The layout follows the executable's own structure: the area a function
belongs to becomes a directory, and the file is named after the function.
