# The SELF container of the retail executable

`USRDIR/EBOOT.BIN` is not a plain ELF: it is a **SELF** container (the
`SCE\0` format) whose payload is NPDRM-encrypted. This document describes
what was measured on the pinned target and how the executable is recovered.

**The decryption itself is not published here.** It needs console key
material, which has no place in a public repository. The method is public
though, and RPCS3 implements it: see `rpcs3/Crypto/unself.cpp`,
`rpcs3/Crypto/key_vault.cpp` and `rpcs3/Crypto/unedat.cpp` in the RPCS3
sources. A contributor with their own console follows the RPCS3 path (the
game's `.rap` file goes to `dev_hdd0/home/<user>/exdata/`), or runs the same
steps with their own tooling.

## The header

| Offset | Size | Field | Value on the target |
|---|---|---|---|
| `0x00` | 4 | magic `SCE\0` | V |
| `0x04` | 2 | version | 0 |
| `0x08` | 2 | key revision | `0x001C` |
| `0x0A` | 2 | header type | `0x0001` (the original SELF) |
| `0x0C` | 4 | metadata offset | `0x0004A000` |
| `0x10` | 8 | header size | `0xA80` |
| `0x18` | 8 | size of the original ELF | 11,158,696 |
| `0x20` | 8 | extension header version | 3 |
| `0x28` | 8 | program information offset | `0x70` |
| `0x30` | 8 | ELF header offset | `0x90` |
| `0x38` | 8 | program header offset | `0xD0` |
| `0x40` | 8 | section header offset | `0xAA46A8` |
| `0x48` | 8 | segment table offset | `0x290` |
| `0x50` | 8 | version header offset | `0x390` |
| `0x58` | 8 | control (supplemental) header offset | `0x3C0` |
| `0x60` | 8 | control header size | `0x100` |

The ELF header at `0x90` is a normal ELF64 big-endian header; its
`e_phoff` and `e_shoff` describe the **rebuilt** ELF, not the SELF's own
layout.

The **size of the original ELF** the container declares - 11,158,696 bytes
- is the size the rebuild must produce, and it is the first check on the
decryption: a wrong licence file gives a container whose declared size and
its decrypted content do not agree.

## The segments

Eight program headers, each with a 32-byte "segment extension" record at
`0x290` giving the file offset, the size, the compression method and the
encryption state of the payload:

| # | payload | size | role |
|---|---|---|---|
| 0 | `0xA80` | `0x8576E0` | the text segment (the code) |
| 1 | - | `0x59A18` | the data segment |
| 2-4 | - | 0 | empty |
| 5 | - | 8 | the TLS block |
| 6 | - | `0x20` | the SCE dynamic section |
| 7 | - | `0x28` | the SCE segment symbols |

The tail of the file (the section header table at `0xAA46A8` and the data
that goes with it) is stored in the clear.

## The NPDRM control information

The supplemental header at `0x3C0` holds the NPDRM control information:

* the licence type: `2` (local licence) on this target,
* the content id: `UP9000-NPUA80965_00-TOOLSOFDESTRUCT1`,
* the program's own key material, encrypted.

The key material comes from the `.rap` file that belongs to the console
(16 bytes). The chain is:

```
rap --(AES-128-CBC, RAP_KEY)--> rif --(rap2rifkey)--> rifkey
rifkey --(AES-128-ECB, NP_KLIC_KEY)--> npdrm_key
metadata_info --(AES-128-CBC, npdrm_key, iv=0)--> metadata_info
metadata_info --(AES-256-CBC, erk, riv)--> metadata_info
metadata_headers --(AES-128-CTR, meta key/iv)--> the section table
each encrypted section --(AES-128-CTR, data key/iv)--> plaintext
```

The `erk`/`riv` pair depends on the key revision (`0x001C` here). A wrong
licence file shows up as a metadata info block whose padding is not zero:
that is the check the tooling does before going further.

## Rebuilding the ELF

The rebuild is mechanical once the segments are decrypted:

1. copy the ELF header and the program headers;
2. write each decrypted segment at its `p_offset`;
3. write the tail (the section header table and the data that goes with it)
   at the offsets the section table names;
4. the result is 11,158,696 bytes and hashes to
   `f9575301e4d403260084ae48700ca248ed27c2d39cfb01049ead448e429df65f`.

That file is what [`tools/ppu_elf.py`](../tools/ppu_elf.py) reads.

## The two containers

The program exists twice: as the **original SELF** (header type `1`) on
the disc, and as the **app** SELF (header type `0x1C`) in the package.
This target's package carries the original form - header type `0x0001` -
and the disc carries the same program.

The disc's copy is **encrypted with the disc key**, a separate key from
the console's NPDRM licence: 64 sectors at LBA 5056 measure 7.999 bits
per byte, so the disc's executable is not readable without it.  The key
for `BCUS98127` is not in the workspace yet.

The difference between the two containers is in the metadata, not in the
program, and both are read by the same method: the header points at the
ELF and at the metadata, and the metadata says how each section is
encrypted.

The sibling project on *A Crack in Time* finds the opposite in its
package: it carries the `app` form.
