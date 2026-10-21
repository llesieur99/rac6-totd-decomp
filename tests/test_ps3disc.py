"""Tests for the PS3 disc reader."""

import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import ps3disc  # noqa: E402


def header(count, table):
    """A first sector with a region table, the way a disc carries it."""
    blob = bytearray(2048)
    blob[0:4] = count.to_bytes(4, "big")
    for index, value in enumerate(table):
        blob[12 + index * 4:16 + index * 4] = value.to_bytes(4, "big")
    return bytes(blob)


class RegionTableTest(unittest.TestCase):
    def test_the_table_is_read(self):
        blob = header(2, [4031, 11667392, 11798495])
        self.assertEqual(ps3disc.region_table(blob), [4031, 11667392, 11798495])

    def test_a_single_region(self):
        blob = header(1, [5165830])
        self.assertEqual(ps3disc.region_table(blob), [5165830])

    def test_the_encrypted_regions_alternate(self):
        # the container is in the clear, the game data is encrypted, the
        # update is in the clear again
        table = [4031, 11667392, 11798495]
        regions = ps3disc.regions_of(table)
        self.assertEqual(regions[0], (0, 4031, False))
        self.assertEqual(regions[1], (4032, 11667391, True))
        self.assertEqual(regions[2], (11667392, 11798495, False))

    def test_only_the_odd_regions_are_encrypted(self):
        table = [4031, 11667392, 11798495]
        self.assertEqual(ps3disc.encrypted_ranges(table), [(4032, 11667391)])

    def test_a_single_region_is_the_container(self):
        self.assertEqual(ps3disc.encrypted_ranges([5165830]), [])

    def test_the_iv_is_the_sector_number(self):
        self.assertEqual(ps3disc.sector_iv(0), b"\x00" * 16)
        self.assertEqual(ps3disc.sector_iv(4032),
                         b"\x00" * 12 + (4032).to_bytes(4, "big"))
        self.assertEqual(ps3disc.sector_iv(0x01020304)[12:],
                         b"\x01\x02\x03\x04")


class KeyTest(unittest.TestCase):
    def test_a_key_is_32_hexadecimal_characters(self):
        self.assertEqual(len(ps3disc.parse_key("0" * 32)), 16)
        self.assertEqual(ps3disc.parse_key("0x" + "1" * 32), b"\x11" * 16)

    def test_a_wrong_key_is_refused(self):
        for bad in ("00", "zz" * 16, "0" * 33, ""):
            with self.assertRaises(ValueError):
                ps3disc.parse_key(bad)


class DerivationTest(unittest.TestCase):
    def test_the_d1_gives_the_disc_key(self):
        # the platform's constants: a d1 of zeros gives a fixed key
        d1 = b"\x00" * 16
        key = ps3disc.disc_key_from_d1(d1)
        self.assertEqual(len(key), 16)
        # the derivation is a single AES-128-CBC pass
        from aes import cbc_encrypt
        self.assertEqual(key, cbc_encrypt(ps3disc.D1_KEY, ps3disc.D1_IV, d1))

    def test_two_d1s_give_two_keys(self):
        self.assertNotEqual(ps3disc.disc_key_from_d1(b"\x00" * 16),
                            ps3disc.disc_key_from_d1(b"\x01" * 16))


class SectorTest(unittest.TestCase):
    def test_a_sector_is_decrypted_on_its_own(self):
        # the same sector, decrypted with two different IVs, gives two
        # different results: the IV is the sector number
        key = b"\x11" * 16
        data = bytes(range(256)) * 8
        first = ps3disc.decrypt_sector(key, 10, data)
        second = ps3disc.decrypt_sector(key, 11, data)
        self.assertNotEqual(first, second)
        self.assertEqual(len(first), len(data))

    def test_the_sector_is_unchanged_in_length(self):
        key = b"\x22" * 16
        data = b"\x00" * 2048
        self.assertEqual(len(ps3disc.decrypt_sector(key, 0, data)), 2048)


if __name__ == "__main__":
    unittest.main()
