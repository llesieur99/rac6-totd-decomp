/*
 * Ratchet & Clank Future: Tools of Destruction (PS3, USA NPUA80965)
 *
 * A parked attempt: the form is right, the compiler's narrowing is not.
 *
 * Target   : USRDIR/EBOOT.BIN, rebuilt PPU ELF
 * Addresses: thirty-nine functions of the target that compare one of
 *            their arguments before doing anything else
 * Compiler : SCEI PPC GCC 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1835 $)
 * Flags    : -O2 -falign-functions=4
 * Result   : **not a match**.  The first difference is at the ninth
 *            byte of the function, where the retail code adds the
 *            offset to the object and the candidate narrows the object
 *            first.
 *
 * The shape
 * ---------
 * These functions compare their second argument with a constant, and
 * then either call a routine or not:
 *
 *     cmpwi   cr7, r4, 0x6f
 *     mflr    r0
 *     addi    r9, r3, 0x140
 *     stdu    r1, -0x70(r1)
 *     std     r0, 0x80(r1)
 *     clrldi  r9, r9, 0x20
 *     beq     cr7, <the end>
 *     bl      <the routine>
 *     nop
 *     mr      r9, r3
 *
 * The result is a pointer into the object the first argument points at,
 * at an offset the code gives, and the comparison decides whether the
 * routine is called at all.
 *
 * The functions, the routine they call, the offset they compute and the
 * value they compare against:
 *
 * | the function | the routine | the offset | the value |
 * |---|---|---|---|
 * | `0x65638` | `0x638F4` | `0x140` | `0x6F` |
 * | `0x69440` | `0x638F4` | `0x140` | `0x6F` |
 * | `0x1AC550` | `0xC3E10` | `0x7F0` | `0x1AB` |
 * | `0x1C8E80` | `0xC3E10` | `0x920` | `0x1AB` |
 * | `0x1D7E6C` | `0xC3E10` | `0x864` | `0x1AB` |
 * | `0x1DBDE4` | `0xC3E10` | `0x8B0` | `0x1AB` |
 * | `0x1E5260` | `0x638F4` | `0x308` | `0xA1` |
 * | `0x1E85C4` | `0x11CDC` | `0x70` | `0x6F` |
 * | `0x1F2820` | `0x11CDC` | `0x80` | `0x6F` |
 * | `0x1F7974` | `0x2579DC` | `0x21D8` | `0x503` |
 * | `0x24AA9C` | `0x11CDC` | `0x1C0` | `0x6F` |
 * | `0x2FFF08` | `0x3044DC` | `0x280` | `0xF4` |
 * | `0x302C14` | `0x26B99C` | `0x20` | `0xF4` |
 * | `0x3044D0` | `0x26B99C` | `0x20` | `0x6F` |
 * | `0x304E5C` | `0x3044DC` | `0x280` | `0xF4` |
 * | `0x309864` | `0x26B99C` | `0x30` | `0xF4` |
 * | `0x3190F4` | `0x26B99C` | `0x68C` | `0xE3` |
 * | `0x3388C0` | `0x26B99C` | `0x60` | `0x6F` |
 * | `0x375DF0` | `0x26B99C` | `0x60` | `0x6C` |
 * | `0x381070` | `0x26B99C` | `0x114` | `0xE3` |
 * | `0x391AA0` | `0x38FC94` | `0x640` | `0x300` |
 * | `0x3A2FF8` | `0x26B99C` | `0x2C` | `0xA1` |
 * | `0x3AFF74` | `0x3B0E2C` | `0x324` | `0xB3` |
 * | `0x3B1AF4` | `0x3B0E2C` | `0x324` | `0x300` |
 * | `0x3E105C` | `0x26B99C` | `0x40` | `0xF4` |
 * | `0x3EBC44` | `0x26B99C` | `0x300` | `0xF4` |
 * | `0x3F4408` | `0x26B99C` | `0x20` | `0xF4` |
 * | `0x3F6448` | `0x26B99C` | `0x20` | `0xF4` |
 * | `0x466BA0` | `0x26B99C` | `0x30` | `0xF4` |
 * | `0x468B1C` | `0x26B99C` | `0x54` | `0x300` |
 * | `0x46EAB8` | `0x46EF60` | `0x20` | `0xF4` |
 * | `0x46EF54` | `0x26B99C` | `0x20` | `0xF4` |
 * | `0x4714A8` | `0x46EF60` | `0x88` | `0x300` |
 * | `0x477A4C` | `0x26B99C` | `0x20` | `0x300` |
 * | `0x489824` | `0x26B99C` | `0x20` | `0x300` |
 * | `0x48D1DC` | `0x489830` | `0x250` | `0xF4` |
 * | `0x48DA04` | `0x3E1068` | `0x138` | `0x562` |
 * | `0x48E1E0` | `0x3E1068` | `0x170` | `0x562` |
 * | `0x4922D8` | `0x26B99C` | `0x40` | `0xF4` |
 *
 * The form that was tried
 * -----------------------
 *     unsigned int wrapper(void *object, int mode)
 *     {
 *         unsigned int result = (unsigned int)(object + 0x140);
 *
 *         if (mode != 0x6f) {
 *             result = routine(object);
 *         }
 *
 *         return result;
 *     }
 *
 * with the object a sixty-four bit pointer, the offset a byte offset,
 * the routine returning a thirty-two bit value, and the comparison
 * written the other way round (`mode == 0x6f` first).
 *
 * The first difference
 * --------------------
 * The retail code adds the offset to the object and truncates the
 * **sum**; the compiler built here narrows the **object** first, and
 * truncates the sum again:
 *
 * | | the retail | the candidate |
 * |---|---|---|
 * | 3 | `addi r9, r3, 0x140` | `mr r9, r3` |
 * | 7 | `clrldi r9, r9, 0x20` | `clrldi r3, r3, 0x20` |
 * | 8 | `beq cr7, ...` | `addi r0, r9, 0x140` |
 *
 * The narrowing is the tree level rewrite of `(T1)(A + C)` into
 * `(T1)A + C`, and the candidate has one instruction more than the
 * retail code.  It is not a flag: twenty-three flags were tried, from
 * `-fno-expensive-optimizations` to `-fno-gcse`, and none of them
 * changes it.
 *
 * The reopening condition
 * -----------------------
 * The retail build used revisions `1826` and `1830` of the compiler; the
 * published sources carry `1835`, the last of the line, and the
 * narrowing is the difference between them.  Two things can open this
 * family again:
 *
 * 1. **Build the revision the retail used.**  The sources of the
 *    revisions `1826` and `1830` are not published, so the project
 *    cannot do it yet; when it can, the thirty-nine functions are one
 *    recipe away.
 * 2. **Find a source form the narrowing does not apply to.**  The
 *    narrowing needs a conversion of a sum, and the sum has to be
 *    narrowed for a reason the compiler can see.  A form in which the
 *    sum is used in a sixty-four bit context - and the truncation is a
 *    separate operation of the source - would keep the two apart.
 */

extern unsigned int sub_638F4(void *object);

unsigned int sub_65638(void *object, int mode)
{
    unsigned int result = (unsigned int)(object + 0x140);

    if (mode != 0x6f) {
        result = sub_638F4(object);
    }

    return result;
}
