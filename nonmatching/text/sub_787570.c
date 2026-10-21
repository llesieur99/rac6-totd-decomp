/*
 * Ratchet & Clank Future: Tools of Destruction (PS3, USA NPUA80965)
 *
 * A parked attempt: the shape is right, the frame is not.
 *
 * Target   : USRDIR/EBOOT.BIN, rebuilt PPU ELF
 * Addresses: twelve small wrappers of the same shape as the nine that
 *            matched - they call one routine and return nothing
 * Compiler : SCEI PPC GCC 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1835 $)
 * Flags    : -O2 -falign-functions=4
 * Result   : **not a match**.  The first difference is at the fourth
 *            byte of the function: the size of the frame.
 *
 * The addresses and the routines they call:
 *
 * | the wrapper | the callee |
 * |---|---|
 * | `0x787570` | `0x789E9C` |
 * | `0x787594` | `0x789EEC` |
 * | `0x7875B8` | `0x789EEC` |
 * | `0x7875DC` | `0x789F24` |
 * | `0x787600` | `0x789F24` |
 * | `0x787624` | `0x789F74` |
 * | `0x787648` | `0x789F74` |
 * | `0x79F654` | `0x78AD5C` |
 * | `0x79F678` | `0x78AA54` |
 * | `0x79F69C` | `0x78AD5C` |
 * | `0x79F6C0` | `0x78AA54` |
 * | `0x7C581C` | `0x78DB90` |
 *
 * The hypothesis
 * --------------
 * The nine wrappers that matched have a frame of 0x70 bytes; these have
 * one of **0x80**.  The sixteen extra bytes are the parameter save area
 * of a floating point argument, which the caller has to reserve when the
 * routine it calls may take one.
 *
 * The source forms that were tried, and the frame each of them gives:
 *
 * | the form | the frame |
 * |---|---|
 * | `void f(void) { g(); }` | 0x70 |
 * | `void f(float a) { g(a); }` | 0x70 |
 * | `void f(double a) { g(a); }` | 0x70 |
 * | `void f(int a) { g(a); }` | 0x70 |
 * | the same with two arguments | 0x70 |
 * | the same, returning an int | 0x70 |
 *
 * None of them reserves the sixteen bytes.  The form that does is not
 * found yet.
 *
 * The reopening condition
 * -----------------------
 * The shape is proved - the prologue, the call, the glue and the
 * epilogue are all there - and only the frame's size is missing.  What
 * is to be found is the form of the source that makes the compiler
 * reserve the parameter save area: the argument the caller passes, and
 * how the callee is declared.  The first difference is at +3, the fourth
 * byte of the function, which is the size of the frame.
 */

extern void sub_789E9C(void);

void sub_787570(void)
{
    sub_789E9C();
}
