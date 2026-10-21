/*
 * Ratchet & Clank Future: Tools of Destruction (PS3, USA NPUA80965)
 *
 * A parked attempt: the source form is right, the build is not.
 *
 * Target   : USRDIR/EBOOT.BIN, rebuilt PPU ELF
 * Address  : 0x6EFD98
 * Extent   : 0x6EFD98 .. 0x6EFE1C (132 bytes, 33 instructions)
 * Compiler : SCEI PPC GCC 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1835 $),
 *            target ppu-lv2
 * Flags    : -O2
 * Result   : **not a match**.  52 of the first 76 bytes are identical;
 *            the first difference is at 0x6EFDCC.
 *
 * The hypothesis
 * --------------
 * This function is the counterpart of the next game's function at
 * 0x6E1760, and the two builds carry the same instructions.  The source
 * below reproduces the retail code up to the return: the first 52 bytes
 * (13 instructions) are identical - the frame, the copy of the float
 * parameter in the caller's frame, the second argument, the call, the
 * sign extension of its result, the comparison and the branch.
 *
 * The first difference
 * --------------------
 * At 0x6EFDCC the two builds differ, and the difference is the *order*
 * of the epilogue, not its content:
 *
 * | | retail | candidate |
 * |---|---|---|
 * | 1 | `ld r0, 0xb0(r1)` | `lfs f1, 0x70(r1)` |
 * | 2 | `lfs f1, 0x70(r1)` | `ld r0, 0xb0(r1)` |
 * | 3 | `lfd f31, 0x98(r1)` | `lfd f31, 0x98(r1)` |
 * | 4 | `mtlr r0` | `addi r1, r1, 0xa0` |
 * | 5 | `addi r1, r1, 0xa0` | `mtlr r0` |
 *
 * and a second difference follows: the retail keeps **two** epilogues
 * (one for the plain return, one for the `v - constant` return), where
 * the candidate computes the difference *before* the branch and shares
 * one epilogue.
 *
 * What was tried
 * --------------
 * * the optimisation levels: `-O0` (the frame differs), `-O1` (the frame
 *   is 0x90, not 0xa0), `-O2` and `-O3` (the same 52 bytes);
 * * `-fno-crossjumping`, `-fno-schedule-insns`, `-fno-schedule-insns2`,
 *   `-fschedule-insns`, `-fno-gcse`, `-fno-tree-pre`: none of them
 *   changes the order of the two loads;
 * * the short-circuit form of the condition (`&&` instead of the nested
 *   `if`): the same code, the same difference;
* *the **other compiler generation**: the SDK 2.7.0 compiler (the one
 *   the sibling project built) produces **exactly** the same 52 bytes and
 *   the same epilogue as this one.  The order is therefore a property of
 *   the source form, not of the compiler revision - the five revisions
 *   between `$Rev: 1835 $` and the retail's `$Rev: 1826 $` are not the
 *   cause.
 *
 * The reopening condition
 * -----------------------
 * Two things have to be recovered, and both are properties of the build
 * rather than of the source:
 *
 * 1. **The order of the epilogue's loads.**  The retail loads the link
 *    register *before* the return value; the compiler built here loads
 *    the return value first.  Something in the retail build - a
 *    scheduling pass, or a source form that puts the return value inside
 *    the epilogue - decides it.  The sibling project found the same kind
 *    of difference in the same place (its three "other readings" are a
 *    few bytes away for a reason of the same family), and it did not
 *    resolve it either.
 * 2. **The TOC slot of the float constant.**  The retail loads it with
 *    `lfs f13, -0x421c(r2)`: a *literal* in the TOC, at the offset the
 *    module's TOC layout gives it.  The candidate loads it from
 *    `-0x8000(r2)`, the offset the minimal link script gives it.  The
 *    slot is a property of the **link**, and reproducing it needs the
 *    module's real TOC layout - which is the same missing piece as the
 *    link layout of the program (see docs/ROADMAP.md, step 5).
 *
 * The first difference is at 0x6EFDCC; the comparison stops there.
 */

extern int sub_6F1978(float *out, int mode);

float sub_6EFD98(float x)
{
    float v = x;
    float saved = x;
    int r = sub_6F1978(&v, 0);

    if ((short)r < 0) {
        if (saved < 0.0f) {
            return v - 1.5f;
        }
    }

    return v;
}
