# The PS3 package container (`.pkg`)

A PlayStation 3 package is a flat container: a header, a content table, a
file table and a data area. The whole payload is XORed with a keystream, so
the reader must decrypt as it goes.

Everything below was measured on the pinned USA package of *Tools of
Destruction* (`UP9000-NPUA80965_00-TOOLSOFDESTRUCT1`) and implemented in
[`tools/pkg.py`](../tools/pkg.py).

## Header (0x00 . 0xFF)

All the integers are big-endian.

| Offset | Size | Field | Value on the target |
|---|---|---|---|
| `0x00` | 4 | magic `7F 50 4B 47` (`\x7FPKG`) | V |
| `0x04` | 2 | revision | `0x8000` |
| `0x06` | 2 | platform | `0x0001` (PS3) |
| `0x08` | 4 | content table offset | `0xC0` |
| `0x0C` | 4 | content count | 8 |
| `0x10` | 4 | header size | `0xC0` |
| `0x14` | 4 | file count | 784 |
| `0x18` | 8 | total size | 16,933,424,960 |
| `0x20` | 8 | data area offset | `0x180` |
| `0x28` | 8 | data area size | 16,933,424,480 |
| `0x30` | 48 | content id, NUL padded | `UP9000-NPUA80965_00-TOOLSOFDESTRUCT1` |
| `0x60` | 16 | digest | `5dcf9abdc5c3e659f044192678c22f8f` |
| `0x70` | 16 | data RIV (the CTR initial counter) | `df09dd7a84883b5f44533aad002d7227` |
| `0xC0` | 8x8 | content table: (index, type) pairs | see below |

The content table of a retail game holds eight entries: the package info,
the package data, the package metadata, the content, the DRM block, the
encrypted content and two more for the large-content variants. The reader
exposes them but does not need them: the file table is enough to extract.

## The file table

The file table starts at the data area offset (`0x180` here) and holds one
32-byte record per entry:

| Offset | Size | Field |
|---|---|---|
| `0x00` | 4 | name offset, relative to the data area |
| `0x04` | 4 | name length |
| `0x08` | 8 | payload offset, relative to the data area |
| `0x10` | 8 | payload size |
| `0x18` | 4 | flags: the low byte is the type (`0x03` file, `0x04` directory) |
| `0x1C` | 4 | padding |

The names live in the data area too, right after the table, and the
directories are entries with type `0x04` and a size of zero.

## The keystream

* **Retail packages** (revision `0x8000`) use AES-128 in counter mode. The
  counter is the 128-bit big-endian value of the data RIV at `0x70`, and the
  key is the platform key (`0x2E 7B 71 D7 C9 C9 A1 4E A3 22 1F 18 88 28 B8 F8`
  for PS3). The counter is incremented once per 16-byte block, starting at
  the RIV.
* **Debug packages** (revision `0x0000`) use a SHA-1 based keystream derived
  from the digest at `0x60`.

The keystream position is the offset **inside the data area**, and every
part of the container is encrypted at its own position: the file table at
`0`, each name at its name offset, each payload at its payload offset.
Getting this wrong is the classic reason for a package that "decrypts" into
garbage.

## Reading the pinned target

```sh
python tools/pkg.py inspect  package.pkg
python tools/pkg.py list     package.pkg --pattern EBOOT
python tools/pkg.py extract  package.pkg --out work/pkg --only EBOOT.BIN
python tools/pkg.py verify   package.pkg --entries
```

The target's layout:

| Entry | Size | Note |
|---|---|---|
| `PS3LOGO.DAT` | 5,120 | |
| `PARAM.SFO` | 1,040 | the title metadata: title `Ratchet & Clank Future: Tools of Destruction`, title id `NPUA80965`, version `01.00`, app version `01.00`, system version `04.3000` |
| `ICON0.PNG`, `ICON1.PAM` | 80,055 / 968,704 | |
| `PIC0..2.PNG`, `SND0.AT3` | | |
| `USRDIR/EBOOT.BIN` | 11,161,440 | the main executable, see [SELF-FORMAT.md](SELF-FORMAT.md) |
| `USRDIR/built/`, `USRDIR/packed/` | 15.8 GiB in total | the game's assets, movies and audio |

The `PARAM.SFO` is **little-endian**, unlike the PPU executable: its magic
is `\0PSF` and its header fields are read with the opposite byte order.

The package holds the retail disc's content, so the working copy needs a lot
of room; extract only what a step needs.

## The package and the disc

The same program exists in two containers, and the difference is worth
recording:

| Source | Container | Header type |
|---|---|---|
| the retail disc (`BCUS98127`) | the original **SELF** | `1` |
| the package (`USRDIR/EBOOT.BIN`) | the repacked **app** | `0x1C` |

Both start with `SCE\0` and both are NPDRM-encrypted with the same licence
file; the metadata they carry is laid out differently, so the two need
different readers.  The package is the convenient one: its header points
straight at the ELF and at the metadata.

The target is a **PlayStation Network** release: the package's content id
carries the `UP9000` prefix, and the licence file that unlocks it
(`UP9000-NPUA80965_00-TOOLSOFDESTRUCT1.rap`) belongs to the console, not
to the disc.  The disc image of the same game has been measured as well:

| Fact | Value |
|---|---|
| image size | 24,163,319,808 bytes (22.50 GiB) |
| volume id | `RATCHET5` |
| format | BD-ROM: an ISO9660 primary descriptor at sector 16 and a UDF 2.01 file set at sector 20 |
| the game data | **encrypted**: 64 sectors at LBA 5056 measure 7.999 bits per byte |

The disc is the **original SELF** container, and its payload is encrypted
with the disc key - a separate key from the console's NPDRM licence.
The key for `BCUS98127` is not in the workspace yet, so the disc's
executable has not been read; the package carries the same program and is
the readable source.
