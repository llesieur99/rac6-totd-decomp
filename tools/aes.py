"""AES-128 in pure Python, plus the CBC and CTR modes.

The PS3 package reader must work on a machine with nothing but the Python
standard library, so the block cipher is implemented here.  When the
``cryptography`` package happens to be installed it is used instead, because
it is orders of magnitude faster; both paths are checked against each other
and against the FIPS-197 vector by the unit tests.

The forward (encryption) direction is what the package reader needs; the
inverse one is what the disc reader needs, and both are here so that a
tool never has to depend on a package to work.
"""

from __future__ import annotations

SBOX = bytes.fromhex(
    "637c777bf26b6fc53001672bfed7ab76"
    "ca82c97dfa5947f0add4a2af9ca472c0"
    "b7fd9326363ff7cc34a5e5f171d83115"
    "04c723c31896059a071280e2eb27b275"
    "09832c1a1b6e5aa0523bd6b329e32f84"
    "53d100ed20fcb15b6acbbe394a4c58cf"
    "d0efaafb434d338545f9027f503c9fa8"
    "51a3408f929d38f5bcb6da2110fff3d2"
    "cd0c13ec5f974417c4a77e3d645d1973"
    "60814fdc222a908846eeb814de5e0bdb"
    "e0323a0a4906245cc2d3ac629195e479"
    "e7c8376d8dd54ea96c56f4ea657aae08"
    "ba78252e1ca6b4c6e8dd741f4bbd8b8a"
    "703eb5664803f60e613557b986c11d9e"
    "e1f8981169d98e949b1e87e9ce5528df"
    "8ca1890dbfe6426841992d0fb054bb16"
)

RCON = (0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36,
        0x6C, 0xD8, 0xAB, 0x4D, 0x9A, 0x2F, 0x5E, 0xBC, 0x63, 0xC6,
        0x97, 0x35, 0x6A, 0xD4, 0xB3, 0x7D, 0xFA, 0xEF, 0xC5, 0x91)

# the inverse substitution table, built from the forward one
INV_SBOX = bytes(0 for _ in range(256))
for _index, _value in enumerate(SBOX):
    INV_SBOX = INV_SBOX[:_value] + bytes([_index]) + INV_SBOX[_value + 1:]


def _xtime(a: int) -> int:
    a <<= 1
    if a & 0x100:
        a = (a ^ 0x1B) & 0xFF
    return a


def _mul(a: int, b: int) -> int:
    out = 0
    for _ in range(8):
        if b & 1:
            out ^= a
        b >>= 1
        a = _xtime(a)
    return out


def expand_key(key: bytes) -> list[list[int]]:
    """Return the eleven AES-128 round keys as lists of sixteen bytes."""
    if len(key) != 16:
        raise ValueError("AES-128 needs a 16-byte key")
    words = [list(key[i * 4:i * 4 + 4]) for i in range(4)]
    for i in range(4, 44):
        temp = list(words[i - 1])
        if i % 4 == 0:
            temp = temp[1:] + temp[:1]
            temp = [SBOX[b] for b in temp]
            temp[0] ^= RCON[i // 4 - 1]
        words.append([a ^ b for a, b in zip(words[i - 4], temp)])
    return [sum(words[r * 4:r * 4 + 4], []) for r in range(11)]


def encrypt_block(key_schedule: list[list[int]], block: bytes) -> bytes:
    state = [b ^ k for b, k in zip(block, key_schedule[0])]
    for rnd in range(1, 11):
        state = [SBOX[b] for b in state]
        # ShiftRows (column-major state: byte index = 4*col + row)
        state = [state[(i + 4 * (i % 4)) % 16] for i in range(16)]
        if rnd != 10:
            out = []
            for c in range(4):
                a0, a1, a2, a3 = state[c * 4:c * 4 + 4]
                out.extend([
                    _mul(a0, 2) ^ _mul(a1, 3) ^ a2 ^ a3,
                    a0 ^ _mul(a1, 2) ^ _mul(a2, 3) ^ a3,
                    a0 ^ a1 ^ _mul(a2, 2) ^ _mul(a3, 3),
                    _mul(a0, 3) ^ a1 ^ a2 ^ _mul(a3, 2),
                ])
            state = out
        state = [b ^ k for b, k in zip(state, key_schedule[rnd])]
    return bytes(state)


class AES128:
    """Pure-Python AES-128, both directions."""

    def __init__(self, key: bytes):
        self._schedule = expand_key(key)

    def encrypt(self, block: bytes) -> bytes:
        if len(block) != 16:
            raise ValueError("AES blocks are 16 bytes")
        return encrypt_block(self._schedule, block)

    def decrypt(self, block: bytes) -> bytes:
        if len(block) != 16:
            raise ValueError("AES blocks are 16 bytes")
        return decrypt_block(self._schedule, block)


def decrypt_block(key_schedule: list[list[int]], block: bytes) -> bytes:
    """The inverse cipher: the same state layout as the forward one."""
    state = [b ^ k for b, k in zip(block, key_schedule[10])]
    for rnd in range(9, -1, -1):
        # InvShiftRows: the row r is rotated right by r
        state = [state[(i - 4 * (i % 4)) % 16] for i in range(16)]
        state = [INV_SBOX[b] for b in state]
        state = [b ^ k for b, k in zip(state, key_schedule[rnd])]
        if rnd:
            out = []
            for c in range(4):
                a0, a1, a2, a3 = state[c * 4:c * 4 + 4]
                out.extend([
                    _mul(a0, 14) ^ _mul(a1, 11) ^ _mul(a2, 13) ^ _mul(a3, 9),
                    _mul(a0, 9) ^ _mul(a1, 14) ^ _mul(a2, 11) ^ _mul(a3, 13),
                    _mul(a0, 13) ^ _mul(a1, 9) ^ _mul(a2, 14) ^ _mul(a3, 11),
                    _mul(a0, 11) ^ _mul(a1, 13) ^ _mul(a2, 9) ^ _mul(a3, 14),
                ])
            state = out
    return bytes(state)


def cbc_encrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
    """AES-128-CBC, encryption."""
    if len(data) % 16:
        raise ValueError("the data is not a whole number of blocks")
    aes = AES128(key)
    fast = _fast_encryptor(key)
    out = bytearray()
    previous = iv
    for offset in range(0, len(data), 16):
        block = bytes(a ^ b for a, b in zip(data[offset:offset + 16], previous))
        if fast is not None:
            previous = fast(block)
        else:
            previous = aes.encrypt(block)
        out += previous
    return bytes(out)


def cbc_decrypt(key: bytes, iv: bytes, data: bytes) -> bytes:
    """AES-128-CBC, decryption."""
    if len(data) % 16:
        raise ValueError("the data is not a whole number of blocks")
    fast = None
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        fast = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor().update
    except Exception:  # pragma: no cover - depends on the host
        fast = None
    aes = AES128(key)
    out = bytearray()
    previous = iv
    for offset in range(0, len(data), 16):
        block = data[offset:offset + 16]
        if fast is not None:
            # the library does the chaining itself
            out += fast(block)
        else:
            plain = aes.decrypt(block)
            out += bytes(a ^ b for a, b in zip(plain, previous))
        previous = block
    return bytes(out)


def _fast_encryptor(key: bytes):
    """Return a callable encrypting one block, using ``cryptography`` if present."""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except Exception:  # pragma: no cover - depends on the host
        return None
    enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return enc.update


class Keystream:
    """A seekable AES-128-CTR keystream, as used by retail PS3 packages.

    The counter is the 128-bit big-endian value given by ``iv``; block ``n``
    uses counter ``iv + n``.
    """

    def __init__(self, key: bytes, iv: bytes):
        if len(iv) != 16:
            raise ValueError("the IV is 16 bytes")
        self._counter = int.from_bytes(iv, "big")
        self._mask = (1 << 128) - 1
        self._fast = _fast_encryptor(key)
        if self._fast is None:
            self._aes = AES128(key)

    def _block(self, index: int) -> bytes:
        counter = (self._counter + index) & self._mask
        raw = counter.to_bytes(16, "big")
        if self._fast is not None:
            return self._fast(raw)
        return self._aes.encrypt(raw)

    def apply(self, data: bytes, offset: int = 0) -> bytes:
        """XOR ``data`` (living at stream position ``offset``) with the keystream."""
        if not data:
            return b""
        index, skip = divmod(offset, 16)
        blocks = bytearray()
        needed = skip + len(data)
        count = (needed + 15) // 16
        for i in range(count):
            blocks += self._block(index + i)
        stream = bytes(blocks[skip:skip + len(data)])
        return bytes(a ^ b for a, b in zip(data, stream))
