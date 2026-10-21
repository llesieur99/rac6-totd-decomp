/*
 * Ratchet & Clank Future: Tools of Destruction (PS3, USA NPUA80965)
 *
 * A small wrapper of the target.
 *
 * Target   : USRDIR/EBOOT.BIN, rebuilt PPU ELF
 * Address  : 0x0070BB1C
 * Extent   : 0x0070BB1C .. 0x0070BB40 (36 bytes, 9 instructions)
 * Compiler : SCEI PPC GCC 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1835 $),
 *            target ppu-lv2 - the published sources of the SDK 1.9.0
 *            generation
 * Flags    : -O2 -falign-functions=4
 * Result   : **byte-exact**.  The 36 bytes at 0x0070BB1C are
 *            reproduced.
 *
 * The proof
 * ---------
 * The candidate is compiled with the compiler that produced the retail
 * build's family, linked at the measured address with the callee at its
 * retail address, and compared with the retail bytes:
 *
 *     python tools/compare_body.py --elf work/eboot/EBOOT.elf \
 *         --object work/gate/sub_70BB1C.elf --address 0x0070BB1C
 *     match: 36 bytes at 0x0070BB1C
 *
 * What the code does
 * ------------------
 * A wrapper: it calls one routine and returns nothing.  The
 * routine it calls is another wrapper of this family.
 *
 * The routine it calls has not been read yet.
 *
 * The name
 * --------
 * `sub_70BB1C` is an alias, not a claim: the function calls one routine and
 * hands the result back, and the routine it calls has not been read
 * yet.  The name says the place, and the place is what the evidence
 * supports.
 *
 * The flags
 * ---------
 * `-falign-functions=4` is not a guess: the retail's functions are
 * aligned on four bytes, and the default of the compiler is eight.  The
 * flag is what puts the body at the retail's address.  The optimisation
 * level is a property of the *file* the function was compiled in, and it
 * is recovered file by file.
 *
 * Reopening condition
 * -------------------
 * The source is a match; it is promoted.  If the build's compiler or its
 * flags ever change, the comparison has to be run again before the body
 * is counted.
 */

extern void sub_7049D8(void);

void sub_70BB1C(void)
{
    sub_7049D8();
}
