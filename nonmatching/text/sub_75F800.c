/*
 * Ratchet & Clank Future: Tools of Destruction (PS3, USA NPUA80965)
 *
 * A parked attempt: the form is right, the call carries no patch point.
 *
 * Target   : USRDIR/EBOOT.BIN, rebuilt PPU ELF
 * Addresses: eight wrappers of the target that call the same routine
 *            with a constant in the second place
 * Compiler : SCEI PPC GCC 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1835 $)
 * Flags    : -O1 -falign-functions=4
 * Result   : **not a match**.  The delay slot of the call holds the
 *            sign extension of the result, where the compiler built
 *            here leaves the `nop` it leaves after a call to a routine
 *            it does not know.
 *
 * The wrappers and the constant they pass:
 *
 * | the wrapper | the routine | the constant |
 * |---|---|---|
 * | `0x75F800` | `0x75F774` | 8 |
 * | `0x75F828` | `0x75F774` | 7 |
 * | `0x75F850` | `0x75F774` | 6 |
 * | `0x75F878` | `0x75F774` | 5 |
 * | `0x75F8A0` | `0x75F774` | 4 |
 * | `0x75F8C8` | `0x75F774` | 3 |
 * | `0x75F8F0` | `0x75F774` | 2 |
 * | `0x75F918` | `0x75F774` | 1 |
 *
 * The form that was tried
 * -----------------------
 *     long wrapper(void *object, int mode, ...)
 *     {
 *         return routine(object, 8, ...);
 *     }
 *
 * with the routine taking nine arguments, the last one floating point -
 * the frame of the wrapper says so - and returning a thirty-two bit
 * value, which the wrapper hands back in sixty-four bits.
 *
 * The first difference
 * --------------------
 * The form reproduces the frame, the constant, the call and the sign
 * extension.  The difference is the delay slot of the call:
 *
 * | | the retail | the candidate |
 * |---|---|---|
 * | 5 | `extsw r3, r3` | `nop` |
 * | 6 | `ld r0, 0x90(r1)` | `extsw r3, r3` |
 *
 * The `nop` is not the compiler's taste: it is the patch point of the
 * linker's TOC-adjusting rule (see [ABI.md](../../docs/ABI.md)).  The
 * compiler leaves it after every call to a routine it does not know,
 * and it leaves none after a call to a routine of the **same
 * translation unit** - a static function - because the TOC pointer
 * cannot change there.
 *
 * So the routine at `0x75F774` is a file-local one, and the eight
 * wrappers belong to its file.
 *
 * The reopening condition
 * -----------------------
 * Reproduce the file-local routine - 140 bytes at `0x75F774` - and the
 * eight wrappers follow.  The body cannot be replaced by a
 * placeholder: the compiler inlines a static function whose body is
 * trivial, and the wrapper then becomes a leaf.  The publication
 * layout has to answer one question at the same time: a static function
 * cannot live in another file, so the wrappers and the routine they
 * call have to be published together.
 */

extern int sub_75F774(void *object, int mode,
                      float value3, float value4, float value5,
                      float value6, float value7, float value8, float value9);

long sub_75F800(void *object, int mode,
                float value3, float value4, float value5,
                float value6, float value7, float value8, float value9)
{
    return sub_75F774(object, 8, value3, value4, value5,
                      value6, value7, value8, value9);
}
