# The retail disc

The target is a PlayStation Network release, and the disc of the same
game is on the share.  The disc is worth measuring for one reason: it
carries the program in its **original SELF container**, where the package
carries it in the repacked one.  It is also the one part of the target
that is not yet read, and this document says why.

## What is measured

| Fact | Value |
|---|---|
| image size | 24,163,319,808 bytes (22.50 GiB) |
| sectors | 11,798,496 (2,048 bytes each) |
| volume id | `RATCHET5` |
| format | ISO9660 (primary descriptor at sector 16) and UDF 2.01 (file set descriptor at sector 20) |
| the container's region table | 3 regions: `[4031, 11667392, 11798495]` |
| the executable | `PS3_GAME/USRDIR/EBOOT.BIN`, at **LBA 4032**, 11,161,440 bytes |
| the game data | **encrypted**: 64 sectors at LBA 5056 measure 7.999 bits per byte |

The container's first sector holds the region table, and the file tree is
in the clear: the platform's own extractor (`extractps3iso`, of the ISO
tools suite) reads it without a key and names the executable's LBA.

The first region - the sectors before 4031 - holds the volume
descriptors and the tree, and it is **in the clear**: the `PARAM.SFO` at
LBA 2049 reads as a valid parameter file.  The game data, from LBA 4032
onwards, is encrypted.

## The scheme

The SDK's own decryption tool documents the scheme, and this is what it
does:

* every **2048-byte sector is decrypted on its own**, with **AES-128-CBC**;
* the **IV is the sector number**: twelve zero bytes and the LBA, big
  endian;
* the key is the **disc key** - sixteen bytes.

The disc key is either given directly (the file the preservation
community publishes, one `.dkey` per disc, as 32 hexadecimal
characters), or derived from the console's own 16-byte value, the "d1",
with one AES-128-CBC pass and two constants of the platform:

```c
disc_key = AES-128-CBC-ENCRYPT(key_d1, iv_d1, d1)

key_d1 = 38 0b cf 0b 53 45 5b 3c 78 17 ab 4f a3 ba 90 ed
iv_d1  = 69 47 47 72 af 6f da b3 42 74 3a ef aa 18 62 87
```

[`tools/ps3disc.py`](../tools/ps3disc.py) implements all of it and takes
the key as an argument; it never writes one.

## The chain, validated

The scheme is not taken on faith: it is checked against the SDK's own
tool, byte for byte.

A synthetic image is built with the layout a disc has - the region table
in the first sector - filled with known bytes, encrypted with the
published disc key of another game, and then decrypted by the SDK's tool.
Every byte the tool produced is the original byte.

That checks the whole chain at once: the way the region table is read,
the IV (the sector number), the AES-128-CBC mode, and the byte order of
the LBA.

The same tool, applied to the target's disc with a candidate key, is
what decides whether a key is right: the executable is at LBA 4032, and
the sector decrypted with the right key starts with the retail
executable's magic.

## Where the key comes from, and what is missing

Two sources, and neither is on this machine:

1. **The preservation community's database.**  One `.dkey` per disc, in
   the same format the SDK's tool expects.  The machine cannot reach it
   (the site refuses the connection), but a browser can.
2. **The console's own key vault.**  The "d1" of every disc the console
   has read is in the vault, and the vault is in the **NAND**, not in the
   NOR.  The console backups on the share are **NOR** dumps: their `eEID`
   region holds the console's identifier and the root key material, and
   nothing else - the search for a DKEY entry in four of them, and a
   brute-force search of every 16-byte window of each of them against the
   target's disc, found no key.

So the disc's executable is **not yet read**, and the target's metadata
says so: `config/target.json` records the disc's facts and leaves the
key empty.

## What the disc would add

The program is the same either way - the package's copy of the executable
decrypts to the ELF the whole project works on - so the disc is not a
blocker for the decompilation.  What it would add is the confirmation
that the two containers carry the same program, and the retail bytes of
the original SELF for the complete-program gate.

The work is one command away: drop the disc's `.dkey` next to the image
and run the tool.
