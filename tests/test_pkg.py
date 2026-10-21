"""Tests for the PS3 package reader, on a synthetic package.

The synthetic package is built in memory with the same layout as a retail
one: a header, a content table, a file table and a data area, all encrypted
the way a retail package is.
"""

import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import aes  # noqa: E402
import pkg  # noqa: E402


def build_package(entries, retail=True, content_id="UP9000-TEST_00-TEST0001"):
    """Build a package holding ``entries`` (a list of (name, payload))."""
    header = bytearray(0x100)
    struct.pack_into(">I", header, 0x00, pkg.MAGIC)
    struct.pack_into(">H", header, 0x04, 0x8000 if retail else 0x0000)
    struct.pack_into(">H", header, 0x06, 1)
    struct.pack_into(">I", header, 0x08, 0xC0)          # content table offset
    struct.pack_into(">I", header, 0x0C, 1)            # content count
    struct.pack_into(">I", header, 0x10, 0xC0)          # header size
    struct.pack_into(">I", header, 0x14, len(entries))  # file count
    struct.pack_into(">Q", header, 0x18, 0)             # total, patched later
    struct.pack_into(">Q", header, 0x20, 0x180)         # data area offset
    struct.pack_into(">Q", header, 0x28, 0)             # data size, patched later
    header[0x30:0x30 + len(content_id)] = content_id.encode("ascii")
    header[0x60:0x70] = bytes(range(16))               # digest
    header[0x70:0x80] = bytes(range(16, 32))            # data riv
    struct.pack_into(">II", header, 0xC0, 1, 4)         # content table entry

    data_offset = 0x180
    table_size = len(entries) * 0x20
    names_total = sum(len(name.encode("utf-8")) for name, _ in entries)
    rows = bytearray()
    name_cursor = table_size
    payload_cursor = table_size + names_total
    for name, payload in entries:
        raw = name.encode("utf-8")
        rows += struct.pack(">II", name_cursor, len(raw))
        rows += struct.pack(">QQ", payload_cursor, len(payload))
        rows += struct.pack(">II", 0x80000003, 0)
        name_cursor += len(raw)
        payload_cursor += len(payload)
    data = bytearray(header)
    data += bytearray(data_offset - len(data))
    data += rows
    for name, _ in entries:
        data += name.encode("utf-8")
    for _, payload in entries:
        data += payload
    struct.pack_into(">Q", data, 0x18, len(data))
    struct.pack_into(">Q", data, 0x28, len(data) - data_offset)

    if retail:
        stream = aes.Keystream(pkg.KEY_PS3, bytes(range(16, 32)))
        table = bytes(data[data_offset:data_offset + table_size])
        data[data_offset:data_offset + table_size] = stream.apply(table, 0)
        # The names and the payloads are encrypted at their own positions.
        cursor = data_offset + table_size
        for name, _ in entries:
            raw = name.encode("utf-8")
            data[cursor:cursor + len(raw)] = stream.apply(raw, cursor - data_offset)
            cursor += len(raw)
        for _, payload in entries:
            data[cursor:cursor + len(payload)] = stream.apply(payload, cursor - data_offset)
            cursor += len(payload)
    else:
        stream = pkg.DebugKeystream(bytes(range(16)))
        table = bytes(data[data_offset:data_offset + table_size])
        data[data_offset:data_offset + table_size] = stream.apply(table, 0)
        cursor = data_offset + table_size
        for name, _ in entries:
            raw = name.encode("utf-8")
            data[cursor:cursor + len(raw)] = stream.apply(raw, cursor - data_offset)
            cursor += len(raw)
        for _, payload in entries:
            data[cursor:cursor + len(payload)] = stream.apply(payload, cursor - data_offset)
            cursor += len(payload)
    return bytes(data)


class PkgTest(unittest.TestCase):
    def setUp(self):
        self.entries = [
            ("PS3LOGO.DAT", b"logo" * 16),
            ("PARAM.SFO", b"sfo"),
            ("USRDIR/EBOOT.BIN", bytes(range(256)) * 8),
            ("USRDIR/built/movie.bin", b"movie" * 100),
        ]

    def _round_trip(self, retail):
        blob = build_package(self.entries, retail=retail)
        with tempfile.NamedTemporaryFile(suffix=".pkg", delete=False) as handle:
            handle.write(blob)
            path = handle.name
        try:
            with pkg.Pkg(path) as package:
                self.assertEqual(package.item_count, len(self.entries))
                names = [e.name for e in package.entries]
                self.assertEqual(names, [name for name, _ in self.entries])
                for entry in package.entries:
                    expected = dict(self.entries)[entry.name]
                    self.assertEqual(package.read(entry), expected)
                    self.assertEqual(package.digest_of(entry),
                                     __import__("hashlib").sha256(expected).hexdigest())
        finally:
            os.unlink(path)

    def test_retail_round_trip(self):
        self._round_trip(retail=True)

    def test_debug_round_trip(self):
        self._round_trip(retail=False)

    def test_selective_extraction(self):
        blob = build_package(self.entries)
        with tempfile.NamedTemporaryFile(suffix=".pkg", delete=False) as handle:
            handle.write(blob)
            path = handle.name
        out = tempfile.mkdtemp()
        try:
            with pkg.Pkg(path) as package:
                hits = package.find("EBOOT")
                self.assertEqual(len(hits), 1)
                target = os.path.join(out, hits[0].name)
                package.extract(hits[0], target)
                with open(target, "rb") as handle:
                    self.assertEqual(handle.read(), dict(self.entries)[hits[0].name])
        finally:
            os.unlink(path)

    def test_bad_magic_is_refused(self):
        with tempfile.NamedTemporaryFile(suffix=".pkg", delete=False) as handle:
            handle.write(b"\x00" * 0x100)
            path = handle.name
        try:
            with self.assertRaises(pkg.PkgError):
                pkg.Pkg(path)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
