"""Reader for Sony PlayStation 3 ``.pkg`` containers.

The container is documented in ``docs/PKG-FORMAT.md``.  Two encryptions are
supported:

* **retail** (finalized) packages, whose payload is XORed with an AES-128-CTR
  keystream built from the header's ``riv`` and the per-platform key;
* **debug** packages, whose payload is XORed with a SHA-1 based keystream
  built from the header's ``digest``.

The reader never writes a game file unless it is asked to, and it can extract
a selected subset of the entries, which keeps the working copy small when a
package holds tens of gigabytes.

    python tools/pkg.py inspect  <package.pkg>
    python tools/pkg.py list     <package.pkg>
    python tools/pkg.py extract  <package.pkg> --out DIR [--only PATTERN ...]
    python tools/pkg.py verify   <package.pkg>

Only the Python standard library is required.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import struct
import sys
from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aes import Keystream  # noqa: E402

MAGIC = 0x7F504B47

# Per-platform keys of the retail package keystream.
KEY_PS3 = bytes([0x2E, 0x7B, 0x71, 0xD7, 0xC9, 0xC9, 0xA1, 0x4E,
                 0xA3, 0x22, 0x1F, 0x18, 0x88, 0x28, 0xB8, 0xF8])
KEY_PSP = bytes([0x07, 0xF2, 0xC6, 0x82, 0x90, 0xB5, 0x0D, 0x2C,
                 0x33, 0x81, 0x8D, 0x70, 0x9B, 0x60, 0xE6, 0x2B])

PLATFORM_NAMES = {1: "PS3", 2: "PSP/Vita"}

SHA1_IV = (0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0)


def _sha1_compress(state: Sequence[int], block: bytes) -> tuple[int, ...]:
    """One SHA-1 compression, with the length field left to the caller."""
    w = list(struct.unpack(">16I", block))
    for i in range(16, 80):
        x = w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16]
        w.append(((x << 1) | (x >> 31)) & 0xFFFFFFFF)
    a, b, c, d, e = state
    for i in range(80):
        if i < 20:
            f, k = (b & c) | (~b & d), 0x5A827999
        elif i < 40:
            f, k = b ^ c ^ d, 0x6ED9EBA1
        elif i < 60:
            f, k = (b & c) | (b & d) | (c & d), 0x8F1BBCDC
        else:
            f, k = b ^ c ^ d, 0xCA62C1D6
        t = ((a << 5) | (a >> 27)) & 0xFFFFFFFF
        t = (t + f + e + k + w[i]) & 0xFFFFFFFF
        e, d, c, b, a = d, c, ((b << 30) | (b >> 2)) & 0xFFFFFFFF, a, t
    return tuple((s + v) & 0xFFFFFFFF for s, v in zip(state, (a, b, c, d, e)))


class DebugKeystream:
    """The SHA-1 keystream of a debug (unfinalized) package."""

    def __init__(self, digest: bytes):
        if len(digest) != 16:
            raise ValueError("the digest is 16 bytes")
        key = digest[0:8] + digest[0:8] + digest[8:16] + digest[8:16]
        self._key = key.ljust(56, b"\x00")
        self._pad = bytearray(64)
        self._pad[0] = 0x80
        self._pad[62] = 0x02

    def _block(self, index: int) -> bytes:
        block = self._key + struct.pack(">Q", index)
        h = _sha1_compress(SHA1_IV, block)
        h = _sha1_compress(h, bytes(self._pad))
        return struct.pack(">4I", *h[:4])

    def apply(self, data: bytes, offset: int = 0) -> bytes:
        if not data:
            return b""
        index, skip = divmod(offset, 16)
        needed = skip + len(data)
        stream = bytearray()
        while len(stream) < needed:
            stream += self._block(index)
            index += 1
        stream = bytes(stream[skip:skip + len(data)])
        return bytes(a ^ b for a, b in zip(data, stream))


@dataclass(frozen=True)
class Entry:
    """One entry of the package file table."""

    name: str
    offset: int          # position of the payload inside the data area
    size: int
    flags: int
    is_dir: bool

    @property
    def type(self) -> int:
        return self.flags & 0xFF


@dataclass(frozen=True)
class ContentInfo:
    """One entry of the package content table."""

    index: int
    type: int
    offset: int
    size: int


class PkgError(Exception):
    """The package is not readable as a PS3 package."""


class Pkg:
    """A Sony PS3 package opened for reading."""

    def __init__(self, path: str):
        self.path = path
        self._file = open(path, "rb")
        try:
            self._read_header()
        except Exception:
            self._file.close()
            raise
        self._entries: list[Entry] | None = None
        self._contents: list[ContentInfo] | None = None

    # -- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "Pkg":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- header ------------------------------------------------------------
    def _read_header(self) -> None:
        head = self._file.read(0x100)
        if len(head) < 0x80:
            raise PkgError("the file is too small to be a package")
        if struct.unpack(">I", head[0:4])[0] != MAGIC:
            raise PkgError("bad magic: this is not a Sony package")
        self.revision = struct.unpack(">H", head[4:6])[0]
        self.platform = struct.unpack(">H", head[6:8])[0]
        self.content_table_offset = struct.unpack(">I", head[8:12])[0]
        self.content_count = struct.unpack(">I", head[12:16])[0]
        self.header_size = struct.unpack(">I", head[16:20])[0]
        self.item_count = struct.unpack(">I", head[20:24])[0]
        self.total_size = struct.unpack(">Q", head[24:32])[0]
        self.data_offset = struct.unpack(">Q", head[32:40])[0]
        self.data_size = struct.unpack(">Q", head[40:48])[0]
        self.content_id = head[0x30:0x60].split(b"\x00")[0].decode("ascii", "replace")
        self.digest = head[0x60:0x70]
        self.riv = head[0x70:0x80]
        self.file_size = os.path.getsize(self.path)
        if self.revision & 0x8000:
            key = KEY_PSP if self.platform == 2 else KEY_PS3
            self._keystream = Keystream(key, self.riv)
            self.encrypted = True
        else:
            self._keystream = DebugKeystream(self.digest)
            self.encrypted = False

    # -- tables ------------------------------------------------------------
    @property
    def entries(self) -> list[Entry]:
        if self._entries is None:
            self._read_entries()
        assert self._entries is not None
        return self._entries

    @property
    def contents(self) -> list[ContentInfo]:
        if self._contents is None:
            self._read_contents()
        assert self._contents is not None
        return self._contents

    def _read_contents(self) -> None:
        self._file.seek(self.content_table_offset)
        raw = self._file.read(self.content_count * 8)
        out = []
        for i in range(self.content_count):
            index, ctype = struct.unpack(">II", raw[i * 8:i * 8 + 8])
            out.append(ContentInfo(index, ctype, 0, 0))
        self._contents = out

    def _read_entries(self) -> None:
        size = self.item_count * 0x20
        self._file.seek(self.data_offset)
        table = self._keystream.apply(self._file.read(size), 0)
        entries = []
        for i in range(self.item_count):
            row = table[i * 0x20:i * 0x20 + 0x20]
            name_offset, name_length = struct.unpack(">II", row[0:8])
            offset, length = struct.unpack(">QQ", row[8:24])
            flags = struct.unpack(">I", row[24:28])[0]
            if name_length == 0 or name_length > 4096:
                raise PkgError(f"the file table is garbage at entry {i}")
            self._file.seek(self.data_offset + name_offset)
            raw_name = self._file.read(name_length)
            name = self._keystream.apply(raw_name, name_offset).decode("utf-8", "replace")
            is_dir = (flags & 0xFF) == 0x04
            entries.append(Entry(name, offset, length, flags, is_dir))
        self._entries = entries

    # -- payload -----------------------------------------------------------
    def read(self, entry: Entry) -> bytes:
        """Return the decrypted payload of ``entry``."""
        if entry.is_dir:
            return b""
        self._file.seek(self.data_offset + entry.offset)
        raw = self._file.read(entry.size)
        if len(raw) != entry.size:
            raise PkgError(f"truncated payload for {entry.name}")
        return self._keystream.apply(raw, entry.offset)

    def extract(self, entry: Entry, destination: str) -> str:
        """Write the decrypted payload of ``entry`` to ``destination``."""
        os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
        with open(destination, "wb") as out:
            chunk = 1 << 20
            done = 0
            self._file.seek(self.data_offset + entry.offset)
            while done < entry.size:
                take = min(chunk, entry.size - done)
                raw = self._file.read(take)
                if len(raw) != take:
                    raise PkgError(f"truncated payload for {entry.name}")
                out.write(self._keystream.apply(raw, entry.offset + done))
                done += take
        return destination

    def find(self, pattern: str) -> list[Entry]:
        """Return the entries whose name contains ``pattern`` (case-insensitive)."""
        needle = pattern.lower()
        return [e for e in self.entries if needle in e.name.lower()]

    def digest_of(self, entry: Entry) -> str:
        """Return the SHA-256 of one entry's payload."""
        return hashlib.sha256(self.read(entry)).hexdigest()

    def package_digest(self) -> str:
        """Return the SHA-256 of the whole package file."""
        digests = hashlib.sha256()
        self._file.seek(0)
        while True:
            chunk = self._file.read(1 << 22)
            if not chunk:
                break
            digests.update(chunk)
        return digests.hexdigest()


def _human(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TiB"


def cmd_inspect(pkg: Pkg, args: argparse.Namespace) -> int:
    print(f"package      : {pkg.path}")
    print(f"size         : {pkg.file_size} bytes ({_human(pkg.file_size)})")
    print(f"platform     : {PLATFORM_NAMES.get(pkg.platform, f'0x{pkg.platform:04X}')}")
    print(f"revision     : 0x{pkg.revision:04X} ({'retail, AES-128-CTR' if pkg.encrypted else 'debug, SHA-1 keystream'})")
    print(f"content id   : {pkg.content_id}")
    print(f"items        : {pkg.item_count}")
    print(f"data area    : 0x{pkg.data_offset:X} .. 0x{pkg.data_offset + pkg.data_size:X}")
    print(f"header size  : {pkg.total_size} (declared total)")
    print(f"digest       : {pkg.digest.hex()}")
    print(f"data riv     : {pkg.riv.hex()}")
    print("content table:")
    for info in pkg.contents:
        print(f"  index {info.index:>4}  type 0x{info.type:02X}")
    files = [e for e in pkg.entries if not e.is_dir]
    dirs = [e for e in pkg.entries if e.is_dir]
    total = sum(e.size for e in files)
    print(f"files        : {len(files)} ({_human(total)}), directories: {len(dirs)}")
    return 0


def cmd_list(pkg: Pkg, args: argparse.Namespace) -> int:
    for entry in pkg.entries:
        if args.pattern and args.pattern.lower() not in entry.name.lower():
            continue
        kind = "<dir>" if entry.is_dir else f"{entry.size:>14}"
        print(f"{entry.flags:08X} {kind}  {entry.name}")
    return 0


def cmd_extract(pkg: Pkg, args: argparse.Namespace) -> int:
    selected: Iterable[Entry] = pkg.entries
    if args.only:
        patterns = [p.lower() for p in args.only]
        selected = [e for e in pkg.entries
                    if not e.is_dir and any(p in e.name.lower() for p in patterns)]
    written = 0
    for entry in selected:
        if entry.is_dir:
            continue
        target = os.path.join(args.out, entry.name.replace("\\", "/"))
        pkg.extract(entry, target)
        written += 1
        print(f"{entry.size:>14}  {target}")
    print(f"{written} file(s) written to {args.out}")
    return 0


def cmd_verify(pkg: Pkg, args: argparse.Namespace) -> int:
    print(f"sha256       : {pkg.package_digest()}")
    if args.entries:
        for entry in pkg.entries:
            if entry.is_dir:
                continue
            print(f"{pkg.digest_of(entry)}  {entry.name}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover - old interpreters
            pass
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("package", help="path to the .pkg file")
        return p

    p_inspect = add("inspect", "print the package header")
    p_inspect.set_defaults(func=cmd_inspect)

    p_list = add("list", "list the file table")
    p_list.add_argument("--pattern", help="only names containing this text")
    p_list.set_defaults(func=cmd_list)

    p_extract = add("extract", "write selected entries to disk")
    p_extract.add_argument("--out", required=True, help="output directory")
    p_extract.add_argument("--only", action="append", help="keep names containing this text (repeatable)")
    p_extract.set_defaults(func=cmd_extract)

    p_verify = add("verify", "hash the package and its entries")
    p_verify.add_argument("--entries", action="store_true", help="also hash every entry")
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    with Pkg(args.package) as pkg:
        return args.func(pkg, args)


if __name__ == "__main__":
    raise SystemExit(main())
