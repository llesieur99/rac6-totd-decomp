"""Tests for the repository guard's listing detector.

The public text may name an instruction - the measurements are built on
them - but it may not carry a listing of the retail code.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import check_repository  # noqa: E402


class ListingTest(unittest.TestCase):
    def test_a_listing_is_detected(self):
        listing = [
            "0x10210:  stdu   r1, -0x70(r1)",
            "0x10214:  mflr   r0",
            "0x10218:  std    r0, 0x80(r1)",
        ]
        for line in listing:
            self.assertTrue(check_repository.LISTING.match(line), line)

    def test_a_listing_without_the_colon(self):
        self.assertTrue(check_repository.LISTING.match("0x6F0250  stdu   r1, -0xa0(r1)"))
        self.assertTrue(check_repository.LISTING.match("0x00010200  bl     0x10638"))

    def test_prose_is_not_a_listing(self):
        # one instruction named in a sentence is a measurement
        self.assertIsNone(check_repository.LISTING.match(
            "the delay slot holds `ld r2, 0x28(r1)` in 22,707 calls"))
        self.assertIsNone(check_repository.LISTING.match(
            "| `ld r2,0x28(r1)` | **22,707** | 28,690 |"))
        self.assertIsNone(check_repository.LISTING.match(
            "the function at 0x6F0250 is 80 bytes long"))
        self.assertIsNone(check_repository.LISTING.match(
            "the compiler leaves a nop there"))

    def test_a_table_of_addresses_is_not_a_listing(self):
        self.assertIsNone(check_repository.LISTING.match("| `0x10210` | 44 | -O1 |"))
        self.assertIsNone(check_repository.LISTING.match(
            "the stub at 0x10200 is four instructions long"))

    def test_the_shape_of_a_stub_is_a_listing(self):
        # the stub of the target, which is exactly the kind of line the
        # guard has to catch
        self.assertTrue(check_repository.LISTING.match("  0x00010200  std    r2, 0x28(r1)"))
        self.assertTrue(check_repository.LISTING.match("  0x00010204  addis  r2, r2, 2"))


if __name__ == "__main__":
    unittest.main()
