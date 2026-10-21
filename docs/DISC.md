# The disc decryption pipeline

A PlayStation 3 disc is not a plain ISO: the game data is encrypted with
the disc's own key.  This document is the pipeline - the tools, the
container's anatomy, the cipher, the three ways to get the key, and the
recipe that was checked against the SDK's own tool.

Everything here was measured on the target's disc and on the tools of the
`SOFTWARE + JAILBREAK` folder, and the cipher was validated byte for byte
against the SDK's own decryption program.

## The tools

| Tool | What it does |
|---|---|
| `PS3 DECRYPTION\PS3DEC\PS3Dec.exe` | **the decryptor**.  A console program: `PS3Dec <mode> <type> [type_op] in [out]` |
| `PS3 DECRYPTION\PS3DEC\PS3Dec R5.7z` | the **source** of that program (`PS3Dec.c`) - the scheme below is read from it, not guessed |
| `PS3 DECRYPTION\PS3DEC\PS3Dec Simple GUI.exe` | a GUI (an AutoHotkey script compiled into an executable): drop an ISO on it and it does the rest |
| `PS3 DECRYPTION\PS3DEC\DKeys\*.dkey` | the disc keys, one file per disc, 32 hexadecimal characters |
| `PS3 DECRYPTION\PS3DEC\Decrypted ISOs.txt` | the GUI's history - **it contains the keys**, so it never leaves the workspace |
| `PS3_ISO_TOOLS_V1.98\extractps3iso.exe` | reads the **file tree** of an image, without a key |
| `PS3_ISO_TOOLS_V1.98\patchps3iso.exe` | **not** a decryptor: it patches an image to a lower firmware version |
| `bkpps3\*.bin` | console backups: **NOR** dumps (the key vault is in the NAND, not here) |

## The container's anatomy

The image is a sequence of **2048-byte sectors**.  Its first sector holds
a **region table**:

```
offset 0    u32  the number of regions, doubled
offset 12   u32  the end of the first region
offset 16   u32  the end of the second region
offset 20   u32  the end of the third region
...
offset 0xF70  16 bytes  the format tag ("Encrypted 3K ISO" / "Decrypted 3K ISO")
offset 0xF80  16 bytes  the disc key, in a 3k3y image
```

The regions **alternate**: the first one is the container, the second one
is the game data, the third one is the update, and so on.  The first and
the third are in the clear; the second is encrypted.  A region that is
encrypted ends **one sector before** its table value, because the table
names the sector *after* the last encrypted one.

The target's disc:

| | |
|---|---|
| image size | 24,163,319,808 bytes (22.50 GiB) |
| sectors | 11,798,496 |
| volume id | `RATCHET5` |
| the table | `[4031, 11667392, 11798495]` |
| region 0 | sectors 0 to 4031 - the container, in the clear |
| region 1 | sectors 4032 to 11667391 - **the game data, encrypted** |
| region 2 | sectors 11667392 to 11798495 - the update, in the clear |
| `PS3_GAME/USRDIR/EBOOT.BIN` | **LBA 4032**, 11,161,440 bytes |

The executable is therefore in the *second* region, at its very first
sector, and the file tree that names it is in the clear: the platform's
own extractor reads it without a key.

## The cipher

Read from the SDK's own source:

* every 2048-byte sector is decrypted **on its own**, with **AES-128-CBC**;
* the **IV is the sector number**: twelve zero bytes and the LBA, big
  endian;
* the key is the **disc key**: sixteen bytes.

```
IV(lba) = 00 00 00 00 00 00 00 00 00 00 00 00 | lba (4 bytes, big endian)
```

## The three ways to get the key

### 1. The published disc key

One `.dkey` file per disc, 32 hexadecimal characters, named after the
disc.  The preservation community publishes them; the GUI's own links are
`redump.org/dkeys/ps3/` and `redump.org/discs/system/ps3/`.

```
PS3Dec d key 1F57B7ED09504ADB8AE8D9DD9B911095 in.iso out.iso
```

### 2. The console's own "d1"

The console stores, for every disc it has read, a 16-byte value: the
"d1".  The disc key is that value processed once, with one AES-128-CBC
pass and two constants of the platform:

```c
disc_key = AES-128-CBC-ENCRYPT(key_d1, iv_d1, d1)

key_d1 = 38 0b cf 0b 53 45 5b 3c 78 17 ab 4f a3 ba 90 ed
iv_d1  = 69 47 47 72 af 6f da b3 42 74 3a ef aa 18 62 87
```

```
PS3Dec d d1 <the d1, 32 hex> in.iso out.iso
```

The d1 lives in the console's **key vault**, which is in the **NAND**
(`dev_flash`), not in the NOR: a console backup taken of the NOR carries
the console's identifier and the root key material, and no d1.  That was
measured here - a search of four NOR backups, structurally and then
brute force over every 16-byte window of each of them, found nothing.

### 3. The 3k3y format

A "3k3y" image carries its own key: the disc key is at offset `0xF80` of
the first sector, and the tag at `0xF70` says whether the image is
encrypted or decrypted.  The tool then needs no key at all:

```
PS3Dec d 3k3y in.iso out.iso
```

This is the format the disc dumper produces on the console.

## The workflow of the GUI

1. the ISO is dropped on the window;
2. the GUI looks for `DKeys\<name>.dkey`; if it is missing, it offers to
   create it, opens it in Notepad and opens the disc's page on the
   preservation site;
3. it reads the key from that file and runs

   ```
   PS3Dec.exe d key <the key> "<the ISO>" "Decrypted ISOs\<the name>.iso"
   ```

4. it records the run, and the key, in `Decrypted ISOs.txt`.

That last file is a key store: it belongs to the private workspace, and
never to a repository.

## The recipe, and how it was checked

[`tools/ps3disc.py`](../tools/ps3disc.py) implements the pipeline with
nothing but the standard library (the block cipher is in
[`tools/aes.py`](../tools/aes.py)), and takes the key as an argument.

The check is not a reading of the source: a synthetic image is built with
the layout a disc has - the region table in the first sector, three
regions, the middle one encrypted - filled with known bytes, encrypted
with a published disc key, and then decrypted **by the SDK's own program**.
The tool says what it did:

```
   Copying sectors        0 to       99
Decrypting sectors      100 to      198
   Copying sectors      199 to      299
```

and every byte it produced is the original byte.  That confirms the
reading of the table, the alternation of the regions, the IV, the mode and
the byte order of the LBA, all at once.

The same chain, applied to a candidate key, is what decides whether the
key is right: the executable is at LBA 4032, and the sector decrypted
with the right key starts with the retail executable's magic.

## What is missing, for this target

The disc key of `BCUS98127` is the one thing the pipeline still waits for:

* the preservation site's database is **not reachable from this machine**
  (the connection is refused), though a browser reaches it;
* the console backups on the share are **NOR** dumps, and the vault that
  holds the d1 is in the NAND.

So the disc's executable is not read yet.  `config/target.json` says so,
and the work is one command away:

```sh
python tools/ps3disc.py sectors "<the image.iso>" <the 32 hex> 4032
```

The package carries the same program and is the readable source, so the
decompilation is not blocked by it.
