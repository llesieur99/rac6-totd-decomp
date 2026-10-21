/*
 * Ratchet & Clank Future: Tools of Destruction (PS3, USA NPUA80965)
 *
 * A small wrapper of the target.
 *
 * Target   : USRDIR/EBOOT.BIN, rebuilt PPU ELF
 * Address  : 0x007875B8
 * Extent   : 0x007875B8 .. 0x007875DC (36 bytes, 9 instructions)
 * Compiler : SCEI PPC GCC 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1835 $),
 *            target ppu-lv2 - the published sources of the SDK 1.9.0
 *            generation
 * Flags    : -O2 -falign-functions=4
 * Result   : **byte-exact**.  The 36 bytes at 0x007875B8 are
 *            reproduced.
 *
 * The proof
 * ---------
 * The candidate is compiled with the compiler that produced the retail
 * build's family, linked at the measured address with the callee at its
 * retail address, and compared with the retail bytes:
 *
 *     python tools/compare_body.py --elf work/eboot/EBOOT.elf \
 *         --object work/gate/sub_7875B8.elf --address 0x007875B8
 *     match: 36 bytes at 0x007875B8
 *
 * What the code does
 * ------------------
 * A wrapper: it calls one routine with its own arguments and returns nothing.
 *
 * The routine it calls has not been read yet.
 *
 * The frame
 * ---------
 * The frame is 0x80 bytes, where the plain wrapper has 0x70.  The
 * sixteen extra bytes are the outgoing argument area of a call to a
 * routine of **nine** arguments: the compiler reserves them as soon as
 * the callee takes more than eight.  The ninth argument is floating
 * point, or it would have to be copied to the stack, and the copy would
 * show in this function - there is none.
 *
 * The types
 * ---------
 * The number of arguments is read from the frame, and their types from
 * the body of the routine that is called: the registers it reads are the
 * arguments it uses.  The arguments it never touches are not determined
 * by the code; they are floating point here, because the last one has
 * to be.
 *
 * The name
 * --------
 * `sub_7875B8` is an alias, not a claim: the function calls one routine
 * and returns nothing, and the routine it calls has not been read yet.
 * The name says the place, and the place is what the evidence supports.
 *
 * The flags
 * ---------
 * `-falign-functions=4` is not a guess: the retail's functions are
 * aligned on four bytes, and the default of the compiler is eight.  The
 * flag is what puts the body at the retail's address.  The optimisation
 * level is a property of the *file* the function was compiled in, and it
 * is recovered file by file: this one is -O2.
 *
 * Reopening condition
 * -------------------
 * The source is a match; it is promoted.  If the build's compiler or its
 * flags ever change, the comparison has to be run again before the body
 * is counted.
 */

extern void sub_789EEC(void *object, float value1, float value2, float value3, float value4, float value5, float value6, float value7, float value8);

void sub_7875B8(void *object, float value1, float value2, float value3, float value4, float value5, float value6, float value7, float value8)
{
    sub_789EEC(object, value1, value2, value3, value4, value5, value6, value7, value8);
}
