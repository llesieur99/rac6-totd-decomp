"""Read and decrypt a PlayStation 3 disc image.

The disc's game data is encrypted with the disc's own key.  The container
of a PS3 disc says which sectors are encrypted: the first sector holds a
region table, and the regions that follow the first one are encrypted.

The scheme, as the SDK's own tool implements it:

* every 2048-byte sector is decrypted on its own, with **AES-128-CBC** and
  an IV made of twelve zero bytes and the **sector number** (big endian);
* the disc key is either given directly, or derived from the console's
  16-byte "d1" with one AES-128-CBC pass and two constants of the
  platform.

The tool reads the region table, the file tree (through the sectors the
container leaves in the clear) and decrypts what is encrypted.  It never
writes a key anywhere: the key is an argument.

    python tools/ps3disc.py info      <image.iso>
    python tools/ps3disc.py tree      <image.iso>
    python tools/ps3disc.py sectors   <image.iso> <key-hex> <lba> [count]
    python tools/ps3disc.py decrypt   <image.iso> <key-hex> <out.iso>

The key is 32 hexadecimal characters (16 bytes).  It is the disc's own
key, published per disc by the preservation community; the key of a disc
the reader owns is the reader's own.
"""

from __future__ import annotations

import argparse
import os
import struct
import sys

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
except ImportError:  # pragma: no cover
    Cipher = None

SECTOR = 2048

# The two constants the platform uses to turn a console's "d1" into a disc
# key.  They are constants of the platform, not secrets.
D1_KEY = bytes([0x38, 0x0B, 0xCF, 0x0B, 0x53, 0x45, 0x5B, 0x3C,
                0x78, 0x17, 0xAB, 0x4F, 0xA3, 0xBA, 0x90, 0xED])
D1_IV = bytes([0x69, 0x47, 0x47, 0x72, 0xAF, 0x6F, 0xDA, 0xB3,
               0x42, 0x74, 0x3A, 0xEF, 0xAA, 0x18, 0x62, 0x87])

# The magic of the retail executable, used to check a decryption.
SELF_MAGIC = b"SCE\x00"


def need_crypto() -> None:
    if Cipher is None:
        raise SystemExit("error: this tool needs the 'cryptography' package")


def region_table(head: bytes) -> list[int]:
    """The region table of a disc image's first sector.

    The first word is a counter and the table follows at offset 12; each
    value is the sector *after* the last one of the region.
    """
    count = int.from_bytes(head[0:4], "big")
    regions = (count * 2) - 1
    if regions < 1:
        raise ValueError("the region table is not there")
    return [int.from_bytes(head[12 + i * 4:16 + i * 4], "big") for i in range(regions)]


def encrypted_ranges(table: list[int]) -> list[tuple[int, int]]:
    """The (first, last) sector of every encrypted region.

    The first region is the container itself: it holds the volume
    descriptors and the file tree, and it is in the clear.
    """
    ranges = []
    start = 0
    for end in table:
        ranges.append((start, end - 1))
        start = end
    return ranges[1:]


def sector_iv(lba: int) -> bytes:
    """The IV of a sector: twelve zero bytes and the sector number."""
    return b"\x00" * 12 + lba.to_bytes(4, "big")


def disc_key_from_d1(d1: bytes) -> bytes:
    """The disc key of a console's "d1"."""
    need_crypto()
    encrypt = Cipher(algorithms.AES(D1_KEY), modes.CBC(D1_IV)).encryptor()
    return encrypt.update(d1) + encrypt.finalize()


def decrypt_sector(key: bytes, lba: int, data: bytes) -> bytes:
    """One sector, decrypted on its own."""
    need_crypto()
    decrypt = Cipher(algorithms.AES(key), modes.CBC(sector_iv(lba))).decryptor()
    return decrypt.update(data) + decrypt.finalize()


def parse_key(text: str) -> bytes:
    """A key: 32 hexadecimal characters, with or without the 0x."""
    if text.lower().startswith("0x"):
        text = text[2:]
    if len(text) != 32:
        raise ValueError("the key must be 32 hexadecimal characters")
    try:
        return bytes.fromhex(text)
    except ValueError:
        raise ValueError("the key contains characters that are not hexadecimal")


def cmd_info(args) -> int:
    with open(args.image, "rb") as handle:
        head = handle.read(4096)
    size = os.path.getsize(args.image)
    table = region_table(head)
    print("image     : %s" % os.path.basename(args.image))
    print("size      : %d bytes (%d sectors)" % (size, size // SECTOR))
    print("regions   : %d" % len(table))
    print("the table : %s" % table)
    for index, (first, last) in enumerate(encrypted_ranges(table)):
        print("  region %d: sectors %d to %d (%d sectors, in the clear: no)"
              % (index + 1, first, last, last - first + 1))
    if table:
        print("  region 0: sectors 0 to %d (the container, in the clear)" % (table[0] - 1))
    tag = head[0xF70:0xF80]
    if tag.strip(b"\x00"):
        print("the tag at 0xF70: %r" % tag)
    return 0


def cmd_sectors(args) -> int:
    key = parse_key(args.key)
    with open(args.image, "rb") as handle:
        handle.seek(args.lba * SECTOR)
        data = handle.read(SECTOR)
    plain = decrypt_sector(key, args.lba, data)
    print("the sector %d, decrypted:" % args.lba)
    print("  the first 16 bytes: %s" % plain[:16].hex(" "))
    if plain[:4] == SELF_MAGIC:
        print("  it starts with the retail executable's magic")
    printable = sum(1 for b in plain if 32 <= b < 127 or b in (9, 10, 13))
    print("  printable bytes: %d of %d (%.1f%%)" % (printable, len(plain),
                                                    100.0 * printable / len(plain)))
    return 0


def cmd_decrypt(args) -> int:
    key = parse_key(args.key)
    with open(args.image, "rb") as handle:
        head = handle.read(4096)
        table = region_table(head)
        ranges = encrypted_ranges(table)
        handle.seek(0)
        total = os.path.getsize(args.image)
        written = 0
        with open(args.out, "wb") as out:
            position = 0
            for first, last in ranges:
                handle.seek(first * SECTOR)
                for lba in range(first, last + 1):
                    block = handle.read(SECTOR)
                    if len(block) < SECTOR:
                        break
                    out.write(decrypt_sector(key, lba, block))
                    written += SECTOR
            # everything the table does not cover is copied as it is
            handle.seek(0)
            while position < total:
                handle.seek(position)
                block = handle.read(SECTOR)
                if not block:
                    break
                out.write(block)
                position += SECTOR
    print("wrote %s: %d bytes decrypted" % (args.out, written))
    return 0


def cmd_tree(args) -> int:
    """The file tree is not read here.

    The tree lives in the UDF file set descriptor, which the platform's
    own extractor reads (`extractps3iso`, the tool of the ISO tools
    suite).  The UDF walk is not implemented in this repository: what the
    project needs from the disc is the *cryptography*, and that is what
    this tool does.
    """
    print("the file tree is read by the platform's own extractor")
    print("  (extractps3iso, from the ISO tools suite)")
    print("  the executable of the target is at the sector the tree names")
    return 0


def find_files(handle, table) -> list[tuple[str, int, int]]:
    """The file tree of a PS3 disc image.

    The tree is in the clear: the UDF file set descriptor and the
    directories it points at live in the container's own region, before
    the encrypted one.
    """
    # the file set descriptor (the UDF tag 9)
    fsd = None
    for lba in range(16, 64):
        handle.seek(lba * SECTOR)
        data = handle.read(SECTOR)
        if len(data) >= 16 and struct.unpack_from("<H", data, 0)[0] == 9:
            fsd = (lba, data)
            break
    if fsd is None:
        raise ValueError("the UDF file set descriptor is not there")
    # its root directory's ICB sits at offset 400 of the descriptor
    root_icb = fsd[1][400:416]
    return walk_directory(handle, root_icb, "", 0)


def icb_extent(icb: bytes) -> tuple[int, int, int]:
    """The (LBA, length, type) of an ICB."""
    length, lba = struct.unpack_from("<II", icb, 0)
    flags = struct.unpack_from("<I", icb, 12)[0]
    kind = flags & 0x0F
    return lba, length, kind


def read_file_entry(handle, lba: int) -> list[tuple[int, int]]:
    """The allocation descriptors of a file entry: (LBA, length) pairs."""
    handle.seek(lba * SECTOR)
    data = handle.read(SECTOR)
    if len(data) < 84 or struct.unpack_from("<H", data, 0)[0] not in (256, 257):
        return []
    extent_length = struct.unpack_from("<Q", data, 56)[0]
    position = 84
    end = 84 + extent_length
    out = []
    while position + 16 <= end and position + 16 <= len(data):
        length, extent = struct.unpack_from("<II", data, position)
        if length == 0 and extent == 0:
            break
        out.append((extent, length))
        position += 16
    return out


def walk_directory(handle, icb: bytes, prefix: str, depth: int) -> list[tuple[str, int, int]]:
    """The files of a directory, and of the directories it holds."""
    lba, _length, _kind = icb_extent(icb)
    extents = read_file_entry(handle, lba)
    if not extents:
        return []
    files: list[tuple[str, int, int]] = []
    for extent_lba, extent_length in extents:
        count = max(1, extent_length // SECTOR)
        handle.seek(extent_lba * SECTOR)
        blob = handle.read(count * SECTOR)
        position = 0
        while position + 38 <= len(blob):
            tag = struct.unpack_from("<H", blob, position)[0]
            if tag != 261:                 # the file identifier descriptor
                break
            record = struct.unpack_from("<H", blob, position + 2)[0]
            if record < 38 or position + record > len(blob):
                break
            name_length = blob[position + 19]
            name = blob[position + 38:position + 38 + name_length].decode("latin1", "replace")
            child = blob[position + 16:position + 32]
            if name and name != "\x00":
                child_lba, _l, _k = icb_extent(child)
                if name == "\x01":
                    pass
                else:
                    files.append((prefix + name, child_lba, 0))
                    if depth < 3:
                        files.extend(walk_directory(handle, child, prefix + name + "/", depth + 1))
            position += record
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    info = sub.add_parser("info", help="the image's layout")
    info.add_argument("image")
    info.set_defaults(func=cmd_info)

    tree = sub.add_parser("tree", help="the file tree")
    tree.add_argument("image")
    tree.set_defaults(func=cmd_tree)

    sectors = sub.add_parser("sectors", help="decrypt one sector")
    sectors.add_argument("image")
    sectors.add_argument("key")
    sectors.add_argument("lba", type=lambda v: int(v, 0))
    sectors.set_defaults(func=cmd_sectors)

    decrypt = sub.add_parser("decrypt", help="decrypt the image")
    decrypt.add_argument("image")
    decrypt.add_argument("key")
    decrypt.add_argument("out")
    decrypt.set_defaults(func=cmd_decrypt)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
