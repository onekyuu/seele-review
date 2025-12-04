import re
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class Hunk:
    old_start: int
    new_start: int
    hunk_lines: List[str]


def split_hunk(diff: str) -> List[Hunk]:
    """split diff into hunks"""
    lines = diff.split('\n')
    hunks: List[Hunk] = []

    current_hunk = Hunk(
        old_start=0,
        new_start=0,
        hunk_lines=[]
    )

    for line in lines:
        if line.startswith('@@'):
            match = re.match(r'@@ -(\d+),?(\d+)? \+(\d+),?(\d+)? @@', line)

            if current_hunk.hunk_lines:
                hunks.append(current_hunk)
                current_hunk = Hunk(
                    old_start=0,
                    new_start=0,
                    hunk_lines=[]
                )

            if match:
                current_hunk.old_start = int(match.group(1))
                current_hunk.new_start = int(match.group(3))

        current_hunk.hunk_lines.append(line)

    if current_hunk.hunk_lines:
        hunks.append(current_hunk)

    return hunks


def computed_hunk_line_number(hunk: Hunk) -> Tuple[List[str], Dict[int, str], Dict[int, str]]:
    """compute line numbers for a hunk"""
    old_start = hunk.old_start
    new_start = hunk.new_start

    temp: List[Tuple[str, str]] = []
    new_hunk_lines: List[str] = [hunk.hunk_lines[0]]
    max_head_length = 0
    old_lines: Dict[int, str] = {}
    new_lines: Dict[int, str] = {}

    # use separate line number counters instead of accumulating based on index
    old_line_number = old_start
    new_line_number = new_start

    for line in hunk.hunk_lines[1:]:
        head = ''

        if line.startswith('-'):
            # delete line: only affects old file line number
            head = f"({old_line_number}, )"
            temp.append((head, line))
            old_lines[old_line_number] = line
            old_line_number += 1
            max_head_length = max(max_head_length, len(head))
        elif line.startswith('+'):
            # add line: only affects new file line number
            head = f"( , {new_line_number})"
            temp.append((head, line))
            new_lines[new_line_number] = line
            new_line_number += 1
            max_head_length = max(max_head_length, len(head))
        else:
            # context line: affects both old and new file line numbers
            head = f"({old_line_number}, {new_line_number})"
            temp.append((head, line))
            old_lines[old_line_number] = line
            new_lines[new_line_number] = line
            old_line_number += 1
            new_line_number += 1
            max_head_length = max(max_head_length, len(head))

    for head, line in temp:
        new_hunk_lines.append(f"{head.ljust(max_head_length)} {line}")

    return new_hunk_lines, new_lines, old_lines
