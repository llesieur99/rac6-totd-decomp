"""Tests for the pure-Python AES-128 used by the package reader."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import aes  # noqa: E402


class AesTest(unittest.TestCase):
    def test_fips_197_vector(self):
        """FIPS-197, appendix B / C.1: the AES-128 example."""
        key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        plain = bytes.fromhex("00112233445566778899aabbccddeeff")
        expected = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
        self.assertEqual(aes.AES128(key).encrypt(plain), expected)

    def test_fast_path_matches_pure_python(self):
        key = bytes(range(16))
        block = bytes(range(16, 32))
        pure = aes.AES128(key).encrypt(block)
        fast = aes._fast_encryptor(key)
        if fast is not None:
            self.assertEqual(fast(block), pure)

    def test_keystream_is_a_seekable_counter(self):
        key = bytes(range(16))
        iv = bytes(range(16, 32))
        stream = aes.Keystream(key, iv)
        data = bytes(range(64))
        whole = stream.apply(data, 0)
        # The same bytes, read from an offset, must give the same result.
        for offset in (0, 1, 15, 16, 17, 31):
            part = stream.apply(data[offset:], offset)
            self.assertEqual(part, whole[offset:], f"offset {offset}")

    def test_keystream_matches_manual_counter(self):
        key = bytes(range(16))
        iv = bytes(range(16, 32))
        stream = aes.Keystream(key, iv)
        data = b"\x00" * 32
        expected = bytearray()
        for index in range(2):
            counter = (int.from_bytes(iv, "big") + index).to_bytes(16, "big")
            expected += aes.AES128(key).encrypt(counter)
        self.assertEqual(stream.apply(data, 0), bytes(expected))


class AesDecryptTest(unittest.TestCase):
    def test_fips_197_vector(self):
        """FIPS-197, appendix C.1: the inverse cipher."""
        key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        cipher = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
        plain = bytes.fromhex("00112233445566778899aabbccddeeff")
        self.assertEqual(aes.AES128(key).decrypt(cipher), plain)

    def test_cbc_round_trip(self):
        key = bytes(range(16))
        iv = bytes(range(16, 32))
        data = bytes(range(64))
        self.assertEqual(aes.cbc_decrypt(key, iv, aes.cbc_encrypt(key, iv, data)), data)

    def test_cbc_matches_the_library(self):
        key = bytes(range(16))
        iv = bytes(range(16, 32))
        data = bytes(range(64))
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        except ImportError:
            self.skipTest("the library is not installed")
        encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
        expected = encryptor.update(data) + encryptor.finalize()
        self.assertEqual(aes.cbc_encrypt(key, iv, data), expected)
        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        self.assertEqual(aes.cbc_decrypt(key, iv, expected),
                         decryptor.update(expected) + decryptor.finalize())


if __name__ == "__main__":
    unittest.main()
