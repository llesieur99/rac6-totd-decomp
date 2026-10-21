"""Tests for the compiler-stamp reader."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import compiler_stamp  # noqa: E402

# The stamps the target carries: two revisions of the same compiler, and
# the libraries the game was linked against.
SAMPLE = (
    b"\x00\x00\x00\x00GCC: (GNU) 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1826 $)\x00"
    b"GCC: (GNU) 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1826 $)\x00"
    b"GCC: (GNU) 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1830 $)\x00"
    b"Lua 5.0.2 Copyright (C) 1994-2004 Tecgraf, PUC-Rio\x00"
)


class CompilerStampTest(unittest.TestCase):
    def test_distinct_stamps(self):
        stamps = compiler_stamp.compiler_stamps(SAMPLE)
        self.assertEqual(len(stamps), 2)
        self.assertEqual(stamps["GCC: (GNU) 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1826 $)"], 2)
        self.assertEqual(stamps["GCC: (GNU) 4.1.1 (CELL 4.1.2.7, RTTI, $Rev: 1830 $)"], 1)

    def test_libraries(self):
        libraries = compiler_stamp.library_stamps(SAMPLE)
        self.assertTrue(any(name.startswith("Lua 5.0.2") for name in libraries))

    def test_no_stamp(self):
        self.assertEqual(compiler_stamp.compiler_stamps(b"nothing here"), {})


if __name__ == "__main__":
    unittest.main()
