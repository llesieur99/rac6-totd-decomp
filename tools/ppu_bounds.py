#!/usr/bin/env python3
"""Recover the *boundaries* of the functions of a stripped PPU executable.

The retail build of a PlayStation 3 game is stripped: it carries no symbol
table and no section names, so every function boundary has to be deduced
from the code itself.

Two cheap scans already exist (``tools/ppu_funcs.py``): a *prologue* scan
that looks for the SDK's ``stdu r1, -N(r1)`` / ``mflr`` opening, and a
*call* scan that collects the targets of the ``bl`` instructions.  Both are
right most of the time, but they are correlated: a prologue in the middle of
a body and a ``bl`` into a block of a body are the two ways the same piece
of code fools them, so they fail together.

This tool adds a third, *independent* opinion, built from the **control
flow** of the code instead of from its opening:

* a function ends where its **epilogue** ends -- the ``ld``/``mtlr``/
  ``addi r1, r1, N``/``blr`` sequence that gives the frame back;
* a function ends where a branch **leaves** it -- a ``b`` that jumps
  outside the body and never comes back (a sibling call), or a ``blr``;
* the instruction that follows a return and that no branch reaches is the
  **opening of the next function**;
* the prologue pattern is *not* used to find the functions: the prologue is
  only read afterwards, to describe a boundary that the flow already
  delimited (and it is reported separately, so the two opinions stay
  distinguishable).

The result is a list of functions with a *start* and an *end*, and any
address that lands strictly inside such a body is not a function: the two
existing scans are wrong about it.

The tool also knows about the **official procedure descriptor** table that
a PPU executable keeps in its ``.opd`` section: it names the procedures the
module exports, with their address and the module's global pointer.  That
table is a *truth* for the function starts, and the tool uses it to measure
the precision and the recall of the three methods.

The tool needs nothing but the Python standard library.

    python tools/ppu_bounds.py functions <eboot.elf> [--out FILE]
    python tools/ppu_bounds.py opd       <eboot.elf> [--out FILE]
    python tools/ppu_bounds.py catalogue <eboot.elf> [--extra FILE] [--out FILE]
    python tools/ppu_bounds.py compare   <eboot.elf> --catalogue FILE [--out DIR]
    python tools/ppu_bounds.py evaluate  <eboot.elf> [--truth FILE] [--verbose N]
"""

from __future__ import annotations

import argparse
import bisect
import heapq
import os
import struct
import sys
from array import array
from dataclasses import dataclass, field
from typing import Sequence

PT_LOAD = 1
SHF_EXECINSTR = 0x4
PF_X = 0x4

# The SDK's frame setup: ``stdu r1, -N(r1)``.
STDU_R1 = 0xF8210000
# ``mflr rX`` is the mfspr family with the extended opcode 0x2A6.
MFLR_MASK = 0xFF1FFCFF
MFLR_VALUE = 0x7C0800A6
# The call instruction.
BRANCH_MASK = 0xFC000001
BRANCH_LINK = 0x48000001


class ElfError(Exception):
    """The file is not a readable PPU ELF."""


# ---------------------------------------------------------------------------
# ELF
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Segment:
    vaddr: int
    filesz: int
    offset: int
    flags: int
    type: int = PT_LOAD


@dataclass(frozen=True)
class Section:
    name: str
    type: int
    flags: int
    addr: int
    offset: int
    size: int


class Elf:
    """The little that this tool needs from the ELF."""

    def __init__(self, data: bytes, name: str = "<memory>"):
        if data[:4] != b"\x7fELF":
            raise ElfError("not an ELF file")
        if data[4] != 2 or data[5] != 2:
            raise ElfError("not a 64-bit big-endian ELF")
        self.data = data
        self.name = name
        self.entry = struct.unpack_from(">Q", data, 0x18)[0]
        phoff = struct.unpack_from(">Q", data, 0x20)[0]
        shoff = struct.unpack_from(">Q", data, 0x28)[0]
        (phentsize, phnum, shentsize, shnum, shstrndx) = \
            struct.unpack_from(">5H", data, 0x36)
        self.segments: list[Segment] = []
        for i in range(phnum):
            off = phoff + i * phentsize
            p_type, p_flags = struct.unpack_from(">II", data, off)
            p_offset, p_vaddr, _p_paddr, p_filesz = struct.unpack_from(">4Q", data, off + 8)
            self.segments.append(Segment(p_vaddr, p_filesz, p_offset, p_flags, p_type))
        self.sections: list[Section] = []
        if shoff and shnum:
            raw = []
            for i in range(shnum):
                off = shoff + i * shentsize
                if off + shentsize > len(data):
                    break
                name_offset, sh_type = struct.unpack_from(">II", data, off)
                sh_flags, sh_addr, sh_offset, sh_size = \
                    struct.unpack_from(">4Q", data, off + 8)
                raw.append((name_offset, sh_type, sh_flags, sh_addr, sh_offset, sh_size))
            names = []
            if shstrndx < len(raw):
                str_off = raw[shstrndx][4]
                for entry in raw:
                    start = str_off + entry[0]
                    end = data.find(b"\x00", start)
                    names.append(data[start:end].decode("ascii", "replace")
                                 if 0 <= start < len(data) else "")
            else:
                names = [""] * len(raw)
            for entry, name in zip(raw, names):
                self.sections.append(Section(name, entry[1], entry[2], entry[3],
                                             entry[4], entry[5]))

    # -- reading -----------------------------------------------------------

    def read_vaddr(self, vaddr: int, length: int) -> bytes:
        """Read *length* bytes at *vaddr* from the segment that holds them."""
        for seg in self.segments:
            if seg.vaddr <= vaddr < seg.vaddr + seg.filesz:
                start = seg.offset + (vaddr - seg.vaddr)
                return self.data[start:start + length]
        raise ElfError(f"no segment holds 0x{vaddr:X}")

    def section_data(self, section: Section) -> bytes:
        return self.data[section.offset:section.offset + section.size]

    # -- the code ----------------------------------------------------------

    def code_ranges(self) -> list[tuple[int, int]]:
        """The (address, size) of the parts of the file that hold code.

        A PPU executable keeps its code, its read-only data and its
        read-write data in a single loadable segment, and the segment
        carries the executable bit; the *sections* are what tell the code
        from the data.  The section names are gone in a retail build, but
        the flags are not, so the sections that carry ``SHF_EXECINSTR``
        are the code.
        """
        ranges: list[tuple[int, int]] = []
        for section in self.sections:
            if section.flags & SHF_EXECINSTR and section.size and section.addr:
                ranges.append((section.addr, section.size))
        if not ranges:
            loadable = [s for s in self.segments
                        if s.flags & PF_X and s.filesz and s.type == PT_LOAD]
            if not loadable:
                raise ElfError("no executable segment found")
            main = max(loadable, key=lambda s: s.filesz)
            start, end = main.vaddr, main.vaddr + main.filesz
            for seg in sorted(loadable, key=lambda s: s.vaddr):
                if seg.vaddr == end:
                    end = seg.vaddr + seg.filesz
            ranges.append((start, end - start))
        ranges.sort()
        merged: list[tuple[int, int]] = []
        for addr, size in ranges:
            if merged and addr <= merged[-1][0] + merged[-1][1]:
                old_addr, old_size = merged[-1]
                merged[-1] = (old_addr, max(old_size, addr + size - old_addr))
            else:
                merged.append((addr, size))
        return merged


# ---------------------------------------------------------------------------
# PPU decoding
# ---------------------------------------------------------------------------

# The instruction classes this tool reasons about.
K_NORMAL = 0   # anything that just falls through
K_CALL = 1     # bl   -- a call to another function
K_JUMP = 2     # b    -- an unconditional jump (sibling call or intra jump)
K_CJUMP = 3    # bc   -- a conditional jump
K_RETURN = 4   # blr  -- the return
K_INDIR = 5    # br / bctr -- a jump to a computed address (jump table)
K_XBR = 6      # a conditional branch to a register (rare)
K_XRET = 7     # beqlr / bdnzlr -- a conditional return

BLR = 0x4E800020
NOP = 0x60000000


def decode(words: Sequence[int], base: int) -> tuple[bytearray, array]:
    """Classify every instruction of *words*.

    Returns a ``kind`` byte per instruction and the absolute target of the
    direct branches.  Only the handful of encodings that carry control flow
    are decoded; the rest is "normal".
    """
    n = len(words)
    kind = bytearray(n)
    target = array("q", bytes(8 * n))
    for index, word in enumerate(words):
        opcode = word >> 26
        if opcode == 18:                      # b / bl
            disp = word & 0x03FFFFFC
            if disp & 0x02000000:
                disp -= 0x04000000
            target[index] = disp if (word >> 1) & 1 else base + 4 * index + disp
            kind[index] = K_CALL if word & 1 else K_JUMP
        elif opcode == 16:                    # bc
            disp = word & 0xFFFC
            if disp & 0x8000:
                disp -= 0x10000
            kind[index] = K_CJUMP
            target[index] = disp if (word >> 1) & 1 else base + 4 * index + disp
        elif opcode == 19:                    # bclr / bcctr / cr
            bo = (word >> 21) & 0x1F
            # the branch field: 0 selects the link register, 1 the counter
            bf = (word >> 10) & 1
            link = word & 1
            if bo == 0:
                pass                          # a condition-register operation
            elif bo == 20:
                if bf == 0:
                    kind[index] = K_RETURN if not link else K_CALL
                else:
                    kind[index] = K_INDIR if not link else K_CALL
            elif bf == 0:
                kind[index] = K_XRET          # beqlr / bdnzlr
            else:
                kind[index] = K_XBR
    return kind, target


# ---------------------------------------------------------------------------
# The official procedure descriptor table
# ---------------------------------------------------------------------------


def opd_functions(elf: Elf, ranges: Sequence[tuple[int, int]]) -> list[int]:
    """The addresses the module's official procedure descriptors name.

    A PPU executable keeps a table of *official procedure descriptors* --
    one per procedure the module exports -- in its ``.opd`` section.  Each
    descriptor is a pair of words: the address of the procedure and the
    module's global pointer.  The ELF entry point points into that table,
    which is how the loader finds the module's entry procedure.

    The descriptors are the module's own list of its functions, so they are
    a *truth* for the function starts -- the only truth a stripped retail
    executable still carries.
    """
    def in_code(address: int) -> bool:
        return any(start <= address < start + size for start, size in ranges)

    entry = elf.entry
    segment = None
    for seg in elf.segments:
        if seg.vaddr <= entry < seg.vaddr + seg.filesz:
            segment = seg
            break
    if segment is None:
        return []
    blob = elf.data[segment.offset:segment.offset + segment.filesz]
    offset = entry - segment.vaddr

    def pair_at(position: int) -> tuple[int, int] | None:
        if position < 0 or position + 8 > len(blob):
            return None
        return struct.unpack_from(">II", blob, position)

    head = pair_at(offset)
    if head is None:
        return []
    _addr, gp = head
    if not gp:
        return []
    table: list[int] = []
    # backwards
    cursor = offset - 8
    while cursor >= 0:
        found = pair_at(cursor)
        if found is None:
            break
        addr, value = found
        if value != gp or not in_code(addr):
            break
        table.append(addr)
        cursor -= 8
    table.reverse()
    # forwards
    cursor = offset
    while True:
        found = pair_at(cursor)
        if found is None:
            break
        addr, value = found
        if value != gp or not in_code(addr):
            break
        table.append(addr)
        cursor += 8
    return sorted(set(table))


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


@dataclass
class Function:
    """One function, as the control flow sees it."""

    start: int
    end: int
    calls: int = 0
    instructions: int = 0

    @property
    def size(self) -> int:
        return self.end - self.start + 4


@dataclass
class RangeAnalysis:
    base: int
    functions: list[Function]
    owner: array                  # index of the function that owns an address
    starts: set[int]
    call_targets: set[int]
    jump_targets: set[int]
    after_return: set[int]
    tail_targets: set[int]
    prologue: set[int]


def frame_table(words: Sequence[int]) -> bytearray:
    """Mark the addresses where a new stack frame is opened.

    The SDK's functions that need a frame open it with ``stdu r1, -N(r1)``.
    A branch that lands on such an address leaves the function it was in:
    no function opens a second frame of its own in the middle of its body.
    """
    marks = bytearray(len(words))
    for index, word in enumerate(words):
        if word & 0xFFFF0000 == STDU_R1 and 0x8000 <= (word & 0xFFFF):
            marks[index] = 1
    return marks


def frame_openers(frames: bytearray, base: int) -> list[int]:
    """The addresses that open a frame, in order."""
    return [base + 4 * index for index, mark in enumerate(frames) if mark]


def _jump_table(words: Sequence[int], base: int, index: int,
                limit: int) -> tuple[int, list[int]]:
    """The jump table that follows a ``bctr``, if it is written inline.

    The PPU compiler writes the table of a dense ``switch`` right after the
    ``bctr`` that dispatches it: a run of 32-bit offsets, relative to the
    table's own address, each one pointing at a case.  The word that
    follows the table is code again, so the table is read as the run of
    small values that opens the block.

    Returns the address just after the table and the list of the cases.
    """
    first = index + 1
    if first >= limit:
        return base + 4 * limit, []
    if not 0 < words[first] < 0x10000:
        # some builds put a second dispatch there; the table follows it
        if first + 1 < limit and 0 < words[first + 1] < 0x10000:
            first += 1
        else:
            return base + 4 * (index + 1), []
    entries = []
    cursor = first
    while cursor < limit and 0 < words[cursor] < 0x10000:
        entries.append(words[cursor])
        cursor += 1
    if len(entries) < 2:
        return base + 4 * (index + 1), []
    table = base + 4 * first
    cases = [table + entry for entry in entries]
    cases = [case for case in cases if base <= case < base + 4 * limit]
    return base + 4 * cursor, cases


def _walk(start: int, kind: bytearray, target: array, words: Sequence[int],
          claimed: bytearray, strong: set[int], known: set[int], frames: bytearray,
          openers: list[int], base: int, n: int, calls_out: list[int],
          returns_out: list[int]) -> tuple[list[int], int, str, int]:
    """Walk the control flow of the function that starts at *start*.

    The walk follows the calls, the forward and backward jumps and the
    conditional branches, and stops on the terminals: a return, a sibling
    call, or an address that another function already owns.  It returns the
    instructions of the body, the last one of them, why the walk ended and
    the address of the sibling call when it ended on one.
    """
    body: list[int] = []
    local: set[int] = set()
    stack = [start]
    end = start
    reason = "empty"
    sibling = 0
    has_return = False
    while stack:
        current = stack.pop()
        while True:
            if current in local:
                reason = "loop"
                break
            index = (current - base) >> 2
            if index < 0 or index >= n:
                reason = "outside"
                break
            if claimed[index]:
                reason = "claimed"
                break
            local.add(current)
            body.append(current)
            if current > end:
                end = current
            k = kind[index]
            if k == K_CALL:
                calls_out.append(target[index])
                current += 4
                if current in known:
                    reason = "claimed"
                    break
                continue
            if k == K_RETURN:
                has_return = True
                reason = "return"
                returns_out.append(current)
                break
            if k == K_JUMP:
                t = target[index]
                tindex = (t - base) >> 2
                if 0 <= tindex < n and claimed[tindex]:
                    reason = "sibling"      # a call into a function we know
                    sibling = t
                    break
                if t in local:
                    reason = "loop"
                    break
                if t < current:
                    current = t             # a backward jump: a loop
                    continue
                if (t in strong or t in known
                        or (0 <= (t - base) >> 2 < n and frames[(t - base) >> 2])):
                    reason = "sibling"      # a tail call to another function
                    sibling = t
                    break
                if openers:
                    # a jump that steps over the opening of another
                    # function leaves the function it was in
                    at = bisect.bisect_right(openers, current)
                    if at < len(openers) and openers[at] < t:
                        reason = "sibling"
                        sibling = t
                        break
                current = t                 # a forward jump inside the function
                continue
            if k == K_CJUMP:
                t = target[index]
                tindex = (t - base) >> 2
                if 0 <= tindex < n and claimed[tindex]:
                    reason = "claimed"
                    break
                stack.append(current + 4)   # the fall-through is always a path
                if t in local:
                    reason = "loop"
                    break
                current = t
                continue
            if k == K_XRET:
                # a conditional return: the path ends here, but the code that
                # follows may still belong to the function
                has_return = True
                reason = "return"
                if current + 4 not in strong:
                    stack.append(current + 4)
                break
            if k == K_INDIR:
                after, cases = _jump_table(words, base, index, n)
                for case in cases:
                    if case not in local:
                        stack.append(case)
                current = after            # the default case follows the table
                continue
            if k == K_XBR:
                reason = "unknown"
                break
            current += 4
            if current in known:
                reason = "claimed"
                break
    return body, end, ("return" if has_return else reason), sibling


def analyse_range(words: Sequence[int], base: int, entry: int,
                  rounds: int = 3, all_returns: bool = False) -> RangeAnalysis:
    """Find the functions of one code range.

    The seeds are the entry point and the call targets; the walk then
    discovers the openings that follow a return.  The result is refined
    over a few rounds: what one round proves to be a function is used as a
    known function by the next one, so that a sibling call is recognised.

    *all_returns* proposes an opening after every return of a function and
    not only after its last one; that finds the functions that follow a
    function with several returns, but it also proposes the cold blocks a
    compiler lays out after a return.
    """
    n = len(words)
    kind, target = decode(words, base)
    frames = frame_table(words)
    openers = frame_openers(frames, base)
    limit = base + 4 * n

    call_targets: set[int] = set()
    jump_targets: set[int] = set()
    # the targets of the branches that stay inside a function: a conditional
    # branch, or a branch that goes backwards.  An address that only a
    # forward jump reaches is the opening of another function.
    inside_targets: set[int] = set()
    for index in range(n):
        k = kind[index]
        if k == K_CALL:
            t = target[index]
            if base <= t < limit:
                call_targets.add(t)
        elif k in (K_JUMP, K_CJUMP):
            t = target[index]
            if base <= t < limit:
                jump_targets.add(t)
                if k == K_CJUMP or t <= base + 4 * index:
                    inside_targets.add(t)

    strong: set[int] = set(call_targets)
    if base <= entry < limit:
        strong.add(entry)
    known: set[int] = set()

    functions: list[Function] = []
    owner = array("i", bytes(4 * n))
    claimed = bytearray(n)
    after_return: set[int] = set()
    tail_targets: set[int] = set()
    confirmed: set[int] = set()

    for _round in range(rounds):
        owner = array("i", bytes(4 * n))
        claimed = bytearray(n)
        functions = []
        after_return = set()
        tail_targets = set()
        confirmed = set()

        heap: list[int] = sorted(strong | call_targets)
        if base <= entry < limit:
            heap.append(entry)
        # the code opens with a function: nothing comes before it
        heap.append(base)
        heapq.heapify(heap)

        while heap:
            start = heapq.heappop(heap)
            index = (start - base) >> 2
            if index < 0 or index >= n:
                continue
            if claimed[index]:
                continue                      # inside a function we already know
            if words[index] == 0:
                continue
            calls: list[int] = []
            returns: list[int] = []
            body, end, reason, sibling = _walk(start, kind, target, words,
                                                claimed, strong, known, frames,
                                                openers, base, n, calls,
                                                returns)
            if reason not in ("return", "sibling"):
                continue                      # not a function, only a block
            if len(body) < 2 and not returns:
                continue                      # too short to be a function
            index_of = len(functions)
            functions.append(Function(start=start, end=end, calls=len(calls),
                                      instructions=len(body)))
            for address in body:
                pos = (address - base) >> 2
                claimed[pos] = 1
                owner[pos] = index_of
            confirmed.add(start)
            if reason == "sibling":
                tail_targets.add(sibling)
            if (reason == "sibling" and sibling
                    and 0 <= (sibling - base) >> 2 < n
                    and frames[(sibling - base) >> 2]):
                # the next function opens where the call left off
                nxt = sibling
                while nxt < limit:
                    word = words[(nxt - base) >> 2]
                    if word != 0 and word != NOP:
                        break
                    nxt += 4
                if nxt < limit and nxt not in inside_targets:
                    after_return.add(nxt)
                    if not claimed[(nxt - base) >> 2]:
                        heapq.heappush(heap, nxt)
            # the opening of the next function: the compiler pads the gap
            # between two functions with nops, and those nops are not the
            # opening of anything
            for ret in (returns if all_returns else [end]):
                nxt = ret + 4
                while nxt < limit:
                    word = words[(nxt - base) >> 2]
                    if word != 0 and word != NOP:
                        break
                    nxt += 4
                if nxt < limit and nxt not in inside_targets:
                    after_return.add(nxt)
                    if not claimed[(nxt - base) >> 2]:
                        heapq.heappush(heap, nxt)

        if confirmed == strong:
            break
        strong = confirmed
        known = confirmed

    # the prologue of each function, read afterwards: it describes the
    # boundary, it does not find it.
    prologue: set[int] = set()
    for func in functions:
        index = (func.start - base) >> 2
        if 0 <= index < n and words[index] & 0xFFFF0000 == STDU_R1:
            prologue.add(func.start)

    starts = {f.start for f in functions}
    return RangeAnalysis(base=base, functions=functions, owner=owner,
                         starts=starts, call_targets=call_targets,
                         jump_targets=jump_targets, after_return=after_return,
                         tail_targets=tail_targets, prologue=prologue)


def analyse(elf: Elf, base: int, size: int, rounds: int = 3,
            all_returns: bool = False) -> RangeAnalysis:
    data = elf.read_vaddr(base, size)
    words = struct.unpack(">%dI" % (len(data) // 4), data)
    return analyse_range(words, base, elf.entry, rounds, all_returns)


# ---------------------------------------------------------------------------
# The two existing scans, for the comparison
# ---------------------------------------------------------------------------


def prologue_candidates(words: Sequence[int], base: int) -> set[int]:
    """The addresses where the SDK's function prologue appears."""
    out = set()
    for index, word in enumerate(words):
        if word & 0xFFFF0000 != STDU_R1:
            continue
        if not 0x8000 <= (word & 0xFFFF):
            continue
        following = words[index + 1] if index + 1 < len(words) else 0
        preceding = words[index - 1] if index > 0 else 0
        if following & MFLR_MASK == MFLR_VALUE or preceding & MFLR_MASK == MFLR_VALUE:
            out.add(base + 4 * index)
    return out


def call_targets(words: Sequence[int], base: int) -> set[int]:
    """The addresses the program calls."""
    out = set()
    for index, word in enumerate(words):
        if word & BRANCH_MASK != BRANCH_LINK:
            continue
        disp = word & 0x03FFFFFC
        if disp & 0x02000000:
            disp -= 0x04000000
        out.add((base + 4 * index + disp) & 0xFFFFFFFFFFFFFFFF)
    return out


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def read_addresses(path: str) -> list[int]:
    addresses = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            field = line.split("\t")[0].strip()
            if field.lower().startswith("0x"):
                try:
                    addresses.append(int(field, 16))
                except ValueError:
                    continue
    return addresses


def _words_of(elf: Elf, base: int, size: int) -> Sequence[int]:
    data = elf.read_vaddr(base, size)
    return struct.unpack(">%dI" % (len(data) // 4), data)


def cmd_opd(elf: Elf, args: argparse.Namespace) -> int:
    ranges = elf.code_ranges()
    table = opd_functions(elf, ranges)
    rows = ["address"]
    rows.extend("0x%08X" % address for address in table)
    text = "\n".join(rows) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"wrote {args.out}: {len(table)} procedures")
    else:
        sys.stdout.write(text)
    return 0


def cmd_functions(elf: Elf, args: argparse.Namespace) -> int:
    ranges = elf.code_ranges()
    rows = ["address\tend\tsize\tevidence\tcalls\tinstructions"]
    total = 0
    for base, size in ranges:
        result = analyse(elf, base, size, args.rounds, args.all_returns)
        total += len(result.functions)
        for func in sorted(result.functions, key=lambda f: f.start):
            evidence = []
            if func.start == elf.entry:
                evidence.append("entry")
            if func.start in result.call_targets:
                evidence.append("call")
            if func.start in result.after_return:
                evidence.append("after-return")
            if func.start in result.tail_targets:
                evidence.append("sibling")
            if func.start in result.prologue:
                evidence.append("prologue")
            rows.append("0x%08X\t0x%08X\t%d\t%s\t%d\t%d" % (
                func.start, func.end, func.size, "+".join(evidence) or "-",
                func.calls, func.instructions))
    text = "\n".join(rows) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"wrote {args.out}: {total} functions")
    else:
        sys.stdout.write(text)
    return 0


def cmd_catalogue(elf: Elf, args: argparse.Namespace) -> int:
    """The merged catalogue: the three methods, with the evidence for each."""
    ranges = elf.code_ranges()
    prologue: set[int] = set()
    calls: set[int] = set()
    starts: set[int] = set()
    for base, size in ranges:
        words = _words_of(elf, base, size)
        prologue |= prologue_candidates(words, base)
        calls |= call_targets(words, base)
        starts |= analyse(elf, base, size, args.rounds, args.all_returns).starts
    extra = set(read_addresses(args.extra)) if args.extra else set()
    rows = ["address\tkind\tevidence"]
    for address in sorted(prologue | calls | starts | extra):
        kind = []
        if address in prologue:
            kind.append("prologue")
        if address in calls:
            kind.append("call")
        if address in starts:
            kind.append("flow")
        if address in extra:
            kind.append("opd")
        if len(kind) == 1:
            evidence = kind[0]
        elif len(kind) == 2:
            evidence = "both"
        else:
            evidence = "all"
        rows.append("0x%08X\t%s\t%s" % (address, "+".join(kind), evidence))
    text = "\n".join(rows) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"wrote {args.out}: {len(rows) - 1} functions")
    else:
        sys.stdout.write(text)
    return 0


def cmd_compare(elf: Elf, args: argparse.Namespace) -> int:
    ranges = elf.code_ranges()
    catalogue = read_addresses(args.catalogue)
    catalogue_set = set(catalogue)
    starts: set[int] = set()
    owner_map: dict[int, int] = {}
    functions: list[Function] = []
    for base, size in ranges:
        result = analyse(elf, base, size, args.rounds, args.all_returns)
        offset = len(functions)
        functions.extend(result.functions)
        starts |= result.starts
        for index, func in enumerate(result.functions):
            for address in range(func.start, func.end + 4, 4):
                owner_map[address] = offset + index

    confirmed, invalidated, uncovered = [], [], []
    for address in catalogue:
        owner = owner_map.get(address, -1)
        if owner < 0:
            uncovered.append(address)
        elif functions[owner].start == address:
            confirmed.append(address)
        else:
            invalidated.append(address)

    new = sorted(starts - catalogue_set)
    lost = sorted(catalogue_set - starts)

    print(f"code ranges       : {', '.join('0x%08X+0x%X' % r for r in ranges)}")
    print(f"functions found   : {len(functions)}")
    print(f"catalogue         : {len(catalogue_set)}")
    print(f"  confirmed       : {len(confirmed)}")
    print(f"  invalidated     : {len(invalidated)}")
    print(f"  not covered     : {len(uncovered)}")
    print(f"new functions     : {len(new)}")
    print(f"catalogue lost    : {len(lost)}")

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        for name, rows in (("confirmed", confirmed), ("invalidated", invalidated),
                           ("uncovered", uncovered), ("new", new),
                           ("lost", lost)):
            with open(os.path.join(args.out, f"{name}.tsv"), "w",
                      encoding="utf-8") as handle:
                handle.write("address\n")
                for address in rows:
                    handle.write("0x%08X\n" % address)
            print(f"  wrote {name}.tsv ({len(rows)})")
    return 0


def _score(candidates: set[int], truth: set[int]) -> tuple[int, int, int, float, float]:
    """(true positives, false positives, false negatives, precision, recall)."""
    hits = len(candidates & truth)
    fp = len(candidates - truth)
    fn = len(truth - candidates)
    precision = hits / len(candidates) if candidates else 0.0
    recall = hits / len(truth) if truth else 0.0
    return hits, fp, fn, precision, recall


def cmd_evaluate(elf: Elf, args: argparse.Namespace) -> int:
    ranges = elf.code_ranges()
    if args.truth:
        truth = set(read_addresses(args.truth))
        source = args.truth
    else:
        truth = set(opd_functions(elf, ranges))
        source = "the official procedure descriptor table"
    if not truth:
        print("error: no truth available", file=sys.stderr)
        return 1

    prologue: set[int] = set()
    calls: set[int] = set()
    starts: set[int] = set()
    for base, size in ranges:
        words = _words_of(elf, base, size)
        prologue |= prologue_candidates(words, base)
        calls |= call_targets(words, base)
        starts |= analyse(elf, base, size, args.rounds,
                           args.all_returns).starts

    print(f"truth             : {len(truth)} addresses ({source})")
    print(f"code ranges       : {', '.join('0x%08X+0x%X' % r for r in ranges)}")
    print()
    print(f"{'method':<24}{'found':>8}{'hits':>8}{'false':>8}{'missed':>8}"
          f"{'precision':>11}{'recall':>9}")
    for name, candidates in (("prologue scan", prologue),
                             ("call scan", calls),
                             ("prologue + call", prologue & calls),
                             ("prologue | call", prologue | calls),
                             ("flow bounds", starts)):
        hits, fp, fn, precision, recall = _score(candidates, truth)
        print(f"{name:<24}{len(candidates):>8}{hits:>8}{fp:>8}{fn:>8}"
              f"{precision:>10.1%}{recall:>9.1%}")
    if args.verbose:
        print()
        for name, candidates in (("prologue scan", prologue),
                                 ("call scan", calls),
                                 ("flow bounds", starts)):
            false = sorted(candidates - truth)
            missed = sorted(truth - candidates)
            print(f"--- {name}: {len(false)} false positives, {len(missed)} missed")
            for address in false[:args.verbose]:
                print(f"    false  0x{address:08X}")
            for address in missed[:args.verbose]:
                print(f"    missed 0x{address:08X}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):  # pragma: no cover
            pass
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("elf", help="path to the PPU ELF")
        p.add_argument("--rounds", type=int, default=3,
                       help="how many refinement rounds to run")
        p.add_argument("--all-returns", action="store_true",
                       help="propose an opening after every return, not only "
                            "after the last one")
        return p

    p_opd = add("opd", "write the official procedure descriptor table")
    p_opd.add_argument("--out", help="write a TSV file instead of stdout")
    p_opd.set_defaults(func=cmd_opd)

    p_functions = add("functions", "write the function boundaries")
    p_functions.add_argument("--out", help="write a TSV file instead of stdout")
    p_functions.set_defaults(func=cmd_functions)

    p_catalogue = add("catalogue", "write the merged catalogue")
    p_catalogue.add_argument("--out", help="write a TSV file instead of stdout")
    p_catalogue.add_argument("--extra",
                             help="a TSV of further addresses to merge in")
    p_catalogue.set_defaults(func=cmd_catalogue)

    p_compare = add("compare", "compare the boundaries with a catalogue")
    p_compare.add_argument("--catalogue", required=True,
                           help="a TSV of candidate addresses")
    p_compare.add_argument("--out", help="directory for the result lists")
    p_compare.set_defaults(func=cmd_compare)

    p_evaluate = add("evaluate", "measure the methods against a truth")
    p_evaluate.add_argument("--truth", help="a TSV of true function addresses")
    p_evaluate.add_argument("--verbose", type=int, default=0,
                             help="list this many false positives and misses")
    p_evaluate.set_defaults(func=cmd_evaluate)

    args = parser.parse_args(argv)
    try:
        with open(args.elf, "rb") as handle:
            elf = Elf(handle.read(), args.elf)
    except (OSError, ElfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return args.func(elf, args)


if __name__ == "__main__":
    raise SystemExit(main())
