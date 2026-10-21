/*
 * Ratchet & Clank Future: Tools of Destruction (PS3, USA NPUA80965)
 *
 * A floating point conversion.
 *
 * Target   : USRDIR/EBOOT.BIN, rebuilt PPU ELF
 * Address  : 0x6F0250
 * Extent   : 0x6F0250 .. 0x6F029F (80 bytes, 20 instructions)
 * Compiler : SCEI PPC GCC 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1835 $),
 *            target ppu-lv2 - the published sources of the SDK 1.9.0
 *            generation
 * Flags    : -O2
 * Result   : **byte-exact**.  The 80 bytes at 0x6F0250 are reproduced.
 *
 * The proof
 * ---------
 *     python tools/compare_body.py --elf work/eboot/EBOOT.elf \
 *         --object work/gate/float_to_short_6f0250.elf --address 0x6F0250
 *     match: 80 bytes at 0x6F0250
 *
 * The same source, in two games
 * -----------------------------
 * This function exists in the next game at `0x6E1C78`, and the two
 * builds carry **the same eighty bytes, instruction for instruction**:
 * the same frame (0xa0), the same copy of the double in the caller's
 * frame, the same reload of the short, the same epilogue.  Only the
 * callee's address differs (here `0x84B3E8`, there `0x903748`).
 *
 * The same source, compiled by two compilers, in two games, produces the
 * same bytes.  That is the strongest evidence the project has that the
 * source form is the authentic one and not a shape that happens to fit.
 *
 * What the code does
 * ------------------
 * The function takes a double and a pointer to an int.  It calls
 * 0x84B3E8 with the address of a local short and the address of the
 * double, stores the (sign extended) short into the caller's int, and
 * returns the double in f1.
 *
 * The two details that make the bytes match
 * ------------------------------------------
 * * The double is passed by address, so the compiler has to keep a copy
 *   of it in memory (0xd0(r1), the caller's frame) and reload it into
 *   f1 after the call: the function returns the double it was given.
 *   Without the "return x", the reload is dead and the compiler drops
 *   it, and the function is 4 bytes short.
 * * The short is reloaded with "lhz" then sign extended with "extsh",
 *   and stored with "stw" into an int.
 *
 * The optimisation level
 * ----------------------
 * | Flags | Result |
 * |---|---|
 * | `-O1` | differs at 0x6F025C, the frame |
 * | **`-O2`** | **80 of 80 bytes** |
 * | `-O3` | **80 of 80 bytes** |
 * | `-Os` | differs at 0x6F025C, the frame |
 *
 * The level is a property of the *file* the function was compiled in, so
 * it is recovered file by file.  The same file in the next game was
 * built at `-O2` as well.
 *
 * What is still a hypothesis
 * --------------------------
 * * The name. "float_to_short" describes the shape of the code, not the
 *   game: the game has no name for it.
 * * The signature of 0x84B3E8.  It is called with (short *, double *).
 *   Its own return value is discarded.
 *
 * Reopening condition
 * -------------------
 * The source is a match; it is promoted.  If the build's compiler or its
 * flags ever change, the comparison has to be run again before the body
 * is counted.
 */

typedef short s16;

extern int sub_84B3E8(s16 *out, double *d);

double float_to_short_6F0250(double x, int *out)
{
    s16 v;

    sub_84B3E8(&v, &x);

    *out = v;

    return x;
}
