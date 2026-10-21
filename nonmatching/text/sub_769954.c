/*
 * Ratchet & Clank Future: Tools of Destruction (PS3, USA NPUA80965)
 *
 * A parked attempt: the shape is right, the call carries no patch point.
 *
 * Target   : USRDIR/EBOOT.BIN, rebuilt PPU ELF
 * Addresses: thirteen small wrappers of the shape the second wave
 *            matched, that call a routine of their **own** file
 * Compiler : SCEI PPC GCC 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1835 $)
 * Flags    : -O1 -falign-functions=4
 * Result   : **not a match**.  The frame and the epilogue are the ones
 *            the second wave's rules give, and the delay slot of the
 *            call holds the reload of the link register instead of the
 *            `nop` the compiler leaves after a call it does not know.
 *
 * The addresses and the routines they call:
 *
 * | the wrapper | the routine of the same file | its size |
 * |---|---|---|
 * | `0x769954` | `0x7696A4` | 188 bytes |
 * | `0x769D84` | `0x769C6C` | 188 bytes |
 * | `0x769EBC` | `0x769DA4` | 188 bytes |
 * | `0x76ABD4` | `0x76AB18` | 188 bytes |
 * | `0x76AD0C` | `0x76AC50` | 188 bytes |
 * | `0x76AE44` | `0x76AD88` | 188 bytes |
 * | `0x76AF7C` | `0x76AEC0` | 188 bytes |
 * | `0x76B0B4` | `0x76AFF8` | 188 bytes |
 * | `0x76B1EC` | `0x76B130` | 188 bytes |
 * | `0x76B308` | `0x76B268` | 160 bytes |
 * | `0x76B3C8` | `0x76B328` | 160 bytes |
 * | `0x76B964` | `0x76B8B8` | 172 bytes |
 * | `0x76D920` | `0x76D69C` | 188 bytes |
 *
 * What the shape says
 * -------------------
 * The wrapper of `0x769954` is the shape the second wave matched, with
 * two differences:
 *
 * * the delay slot of the call holds the reload of the link register,
 *   where the wrappers of the wave hold the `nop` the compiler leaves
 *   after a call;
 * * the frame is 0x80, and the routine of the same file takes nine
 *   arguments, the last one floating point - the rule the second wave
 *   measured.
 *
 * The `nop` is not the compiler's taste: it is the patch point of the
 * linker's TOC-adjusting rule (see [ABI.md](../../docs/ABI.md)).  The
 * compiler leaves it after every call to a routine it does not know,
 * and it leaves none after a call to a routine of the **same
 * translation unit** - a static function - because the TOC pointer
 * cannot change there.
 *
 * So the routine at `0x7696A4` is a file-local one, and the wrapper and
 * it belong to the same source file.
 *
 * Why it is parked
 * ----------------
 * The wrapper's own bytes are reachable: the frame and the epilogue are
 * the ones the second wave's rules give.  What is missing is the
 * *routine* the wrapper calls - 188 bytes of code that has not been
 * reproduced yet.
 *
 * It cannot be replaced by a placeholder: the compiler inlines a static
 * function whose body is trivial, and the wrapper then becomes a leaf.
 * The bytes of the wrapper only appear when the body of the routine is
 * the authentic one, and the routine's body is a function of its own
 * that has to be matched on its own.  The source below is the attempt
 * that was made, with the trivial body: the compiler inlines it, and
 * the wrapper comes out four bytes long.
 *
 * The reopening condition
 * -----------------------
 * Reproduce the file-local routine - `0x7696A4` and its twelve
 * siblings, which are the same routine with different constants - and
 * the wrapper follows.  The publication layout has to answer one
 * question at the same time: a static function cannot live in another
 * file, so the wrapper and the routine it calls have to be published
 * together.
 */

static void helper(void *p, int a, int b,
                   float c, float d, float e, float f, float g, float h)
{
    (void)p;
    (void)a;
    (void)b;
    (void)c;
    (void)d;
    (void)e;
    (void)f;
    (void)g;
    (void)h;
}

void sub_769954(void *p, int a, int b,
                float c, float d, float e, float f, float g, float h)
{
    helper(p, a, b, c, d, e, f, g, h);
}
