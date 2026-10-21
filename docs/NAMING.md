# Naming the functions

A matching decompilation has to *earn* every name it uses: the executable
is stripped, so a name is a claim that has to be supported by the code, by
the callers, by the data the function touches, or by the module it belongs
to.  This document records the method that turns the retail build's own
leftovers into such names.

The names themselves stay in the contributor's workspace: they are the
game's, and the repository never carries game data.  What is published here
is the method and its measurements.

## What the retail build leaves behind

The target's executable is stripped of its symbol table, and its section
names are gone, but two things survive, and each of them names things.

### The assertion messages

The build keeps the messages of its assertions, and an assertion names the
file, the line and usually the condition it comes from:

```
<file>:<line> (<condition>)
```

The target carries **35** messages of that form, and they are the raw
material of the naming: each one names a source file, and the file names
a module of the studio's tree.

The *whole* message table of a module is kept, and the messages carry the
method names with them, so one module's messages can name dozens of
methods at once.

### The strings themselves

**9,358** strings of eight characters or more are readable in the
target's executable (the same scan on the next game's executable finds
18,515).  They are the raw material of the naming: every one of them is a
candidate for naming the function that reads it.

## The bridge: from a string to a name

A string on its own names nothing; it is the *reference* to it that names
the function.  The chain is short and every step of it is checkable:

1. the global variable's address is reached through the TOC, and the
   compiler's own way of reaching it is a load from `r2`;
2. a data-flow analysis over the function follows the registers and finds
   the load that reads the string;
3. the load sits in a function, and the function's boundaries are known
   (see [CATALOGUE.md](CATALOGUE.md));
4. the string says which method, and the assertion says which file and
   line.

The target's own code shows how the TOC is reached, and the global
pointer is the one the module descriptor names:

```
entry point (module descriptor) : 0x00874050
descriptor[1] (the TOC base)    : 0x008AB078
```

From then on, a global is a signed 16-bit displacement from `r2`, and the
catalogue of the globals is in [GLOBALS.md](GLOBALS.md).

## What the method gives

* every function that reads an assertion message has a **name**, a
  **source file** and a **line**;
* every function that reads a named global works on a **type**, which
  gives its parameters and its return value;
* the **module** a function belongs to follows from the descriptor, which
  is what gives a name to the functions that touch nothing but the code.

## What is still missing

* The names of the functions that read no string and touch no global: for
  them, the module they belong to and their callers are the only
  evidence, and the name has to stay a description of the place
  (`module_init` in `src/text/`).
* The type information: this build carries no RTTI, so the shapes of the
  engine's classes have to come from the code and from the sibling
  projects, not from a table of names.
* The third-party libraries' names come from their own sources, which
  are not the studio's and are not in the repository.
