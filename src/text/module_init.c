/*
 * Ratchet & Clank Future: Tools of Destruction (PS3, USA NPUA80965)
 *
 * The engine's initialisation function.
 *
 * Target   : USRDIR/EBOOT.BIN, rebuilt PPU ELF
 * Address  : 0x10210
 * Extent   : 0x10210 .. 0x1023C (44 bytes, 11 instructions)
 * Compiler : SCEI PPC GCC 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1835 $),
 *            target ppu-lv2 - the published sources of the SDK 1.9.0
 *            generation.  The retail build used revisions 1826 and 1830.
 * Flags    : -O1
 * Result   : **byte-exact**.  The 44 bytes at 0x10210 are reproduced.
 *
 * The proof
 * ---------
 * The candidate is compiled with the compiler that produced the retail
 * build's family, linked at the measured address with the callees at
 * their retail addresses, and compared with the retail bytes:
 *
 *     python tools/compare_body.py --elf work/eboot/EBOOT.elf \
 *         --object work/gate/module_init.elf --address 0x10210
 *     match: 44 bytes at 0x10210
 *
 * The link step matters
 * ---------------------
 * The compiler alone is 24 bytes short: the retail code has
 * `ld r2, 0x28(r1)` in the delay slot of the second call, where the
 * compiler leaves a `nop`.  That is the SDK's own rule, written down in
 * its own header:
 *
 *     /* place a nop after the call so that the linker can restore the
 *        TOC pointer if a TOC adjusting call stub is needed.  */
 *
 * The second call goes to a TOC-adjusting stub (0x10200), and the linker
 * puts the TOC restore in the slot the compiler reserved.  The rule is
 * measured on the retail build: **every** call to a stub carries the
 * restore (22,707 of them) and **no** other call does.  See
 * [docs/ABI.md](../docs/ABI.md) and [tools/ppu_stubs.py](../tools/ppu_stubs.py).
 *
 * What the code does
 * ------------------
 * It calls two functions in a row and returns nothing.  The first
 * (0x146AC) reads a table of global data through the global pointer and
 * dispatches through a function pointer.  The second call goes through
 * the stub at 0x10200, which switches the TOC base and jumps to the
 * routine that registers a destructor (0x864598).
 *
 * The prologue and the epilogue are the SDK's: the frame is 0x70 bytes,
 * the link register is saved in the caller's frame at 0x10(r1), and the
 * stack pointer is restored with an immediate add.
 *
 * The optimisation level
 * ----------------------
 * `-O1` is the only level that reproduces the bytes:
 *
 * | Flags | Result |
 * |---|---|
 * | `-O0` | differs at 0x10213, the frame |
 * | **`-O1`** | **44 of 44 bytes** |
 * | `-O2` | differs at 0x10230, the epilogue |
 * | `-O3` | differs at 0x10230, the epilogue |
 * | `-Os` | differs at 0x10230, the epilogue |
 *
 * The difference at `-O2` is the order of the epilogue: the compiler
 * restores the stack pointer before the link register, where the retail
 * code does the opposite.  The optimisation level is a property of the
 * *file* the function was compiled in, so it is recovered file by file.
 *
 * What is still a hypothesis
 * --------------------------
 * * The name. "module_init" describes the place: this is the first
 *   function of the text segment, the section the loader runs at
 *   start-up.  The game's own name for it is unknown.
 * * The two callees.  Their names here are addresses; what they do is
 *   still to be read.
 *
 * Reopening condition
 * -------------------
 * The source is a match; it is promoted.  If the build's compiler or its
 * flags ever change, the comparison has to be run again before the body
 * is counted.
 */

void sub_146AC(void);
void sub_10200(void);

void module_init(void)
{
    sub_146AC();

    sub_10200();
}
