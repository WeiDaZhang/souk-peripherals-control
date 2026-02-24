#!/usr/bin/env python3
"""
extract_bias_debug.py

Extract groups of the following debug lines (in this order) from a log file:
  - DEBUG - Local voltage
  - DEBUG - Remote voltage:
  - DEBUG - Bias current:
  - DEBUG - Top drop voltage:

Usage:
    python3 extract_bias_debug.py /path/to/souk_lna_bias_control_monitor.log [output.csv]

If output CSV path is omitted, writes to ./extracted_debug.csv
"""

from dataclasses import dataclass
import sys
import re
import csv
from pathlib import Path
from typing import List, Tuple, Dict
from collections import defaultdict

import matplotlib.pyplot as plt

# The exact ordered prefixes we look for (in this order).
PREFIXES = [
    "DEBUG - Local voltage",
    "DEBUG - Remote voltage",
    "DEBUG - Bias current",
    "DEBUG - Top drop voltage",
]

# compile a regex to match lines that start with a prefix (allow optional colon/space after)
PREFIX_RE = re.compile(
    r".*?(DEBUG - (Local voltage|Remote voltage|Bias current|Top drop voltage))"
    r":?\s*(.*)"
)


@dataclass
class ExtractedDataPoint:
    start_line: int
    end_line: int
    local_voltage: float
    remote_voltage: float
    bias_current: float
    top_drop_voltage: float
    estimated_lna_voltage: float = 0.0

    def __post_init__(self):
        self.local_voltage = float(self.local_voltage.removesuffix(" V"))
        self.remote_voltage = float(self.remote_voltage.removesuffix(" V"))
        self.bias_current = float(self.bias_current.removesuffix(" mA")) / 1000
        self.top_drop_voltage = float(self.top_drop_voltage.removesuffix(" V"))
        self.estimated_lna_voltage = self.remote_voltage - self.top_drop_voltage / 2


def scan_matches(log_path: Path) -> List[Tuple[int, str, str]]:
    """
    Return list of (lineno, prefix_key, value_str) for each matching prefix in file.
    value_str may be "" if not present on same line (we will attempt to grab next non-empty line).
    """
    matches = []
    with log_path.open("r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()

    # Prestrip newline but keep original for lineno mapping
    for idx, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        m = PREFIX_RE.match(line)
        if m:
            prefix_text = m.group(1)
            value = m.group(3).strip()
            # try to normalize the prefix to our keys (match by startswith)
            # find which entry in PREFIXES starts with prefix_text
            matched_key = None
            for key in PREFIXES:
                if prefix_text.startswith(key):
                    matched_key = key
                    break
            if matched_key:
                # value = line_value_after_colon(line)
                matches.append((idx, matched_key, value))
    # Also keep lines list for next-line value lookups
    return matches, lines


def grab_next_nonempty_line(lines: List[str], start_idx: int) -> str:
    """
    start_idx is 1-based line number after which to search (i.e., start_idx+1 ..)
    Returns stripped content or "" if none.
    """
    for i in range(start_idx, len(lines)):
        txt = lines[i].strip()
        if txt != "":
            return txt
    return ""


def group_sequences(
    matches: List[Tuple[int, str, str]], lines: List[str]
) -> List[Dict]:
    """
    From the linear list of matches produce groups where the 4 prefixes appear in order.
    For each group, return a dict with values for each prefix plus start/end lineno.
    """
    results = []
    # Build index by scanning possible starts
    n = len(matches)
    for i in range(n):
        lineno_i, key_i, val_i = matches[i]
        if key_i != PREFIXES[0]:
            continue  # only start at the first prefix
        # attempt to find subsequent keys in order
        group = {PREFIXES[0]: (lineno_i, val_i)}
        ok = True
        last_pos = i
        for target in PREFIXES[1:]:
            # search for next match with matched key == target and lineno greater than previous
            found = None
            for j in range(last_pos + 1, n):
                if matches[j][1] == target:
                    found = (j, matches[j])
                    break
            if not found:
                ok = False
                break
            j_idx, (lineno_j, key_j, val_j) = found
            group[key_j] = (lineno_j, val_j)
            last_pos = j_idx
        if not ok:
            continue
        # For each value, if empty, try to capture next non-empty line after its lineno
        for key in PREFIXES:
            lineno_k, val_k = group[key]
            if not val_k:
                next_line = grab_next_nonempty_line(lines, lineno_k)
                group[key] = (lineno_k, next_line)
        # Build a clean result dict mapping short names to values
        # result = {
        #     "local_voltage": group[PREFIXES[0]][1],
        #     "remote_voltage": group[PREFIXES[1]][1],
        #     "bias_current": group[PREFIXES[2]][1],
        #     "top_drop_voltage": group[PREFIXES[3]][1],
        #     "start_line": group[PREFIXES[0]][0],
        #     "end_line": group[PREFIXES[3]][0],
        # }
        result = ExtractedDataPoint(
            start_line=group[PREFIXES[0]][0],
            end_line=group[PREFIXES[3]][0],
            local_voltage=group[PREFIXES[0]][1],
            remote_voltage=group[PREFIXES[1]][1],
            bias_current=group[PREFIXES[2]][1],
            top_drop_voltage=group[PREFIXES[3]][1],
        )
        results.append(result)
    return results


def print_results(results: List[ExtractedDataPoint], start_idx=0, end_idx=-1):
    if not results:
        print(
            "No complete sequences found (the four prefixes did not appear in order)."
        )
        return
    # pretty print table-like
    print(f"Print {end_idx - start_idx + 1} sequence(s):\n")
    for idx, r in enumerate(results[start_idx:end_idx], start=1):
        print(f"Sequence {idx}  (lines {r.start_line}..{r.end_line}):")
        print(f"  Local voltage  : {r.local_voltage} V")
        print(f"  Remote voltage : {r.remote_voltage} V")
        print(f"  Bias current   : {r.bias_current} mA")
        print(f"  Top drop voltage. : {r.top_drop_voltage} V")
        print(f"  Estimated LNA voltage: {r.estimated_lna_voltage} V")
        print("-" * 60)

    # print in {v bias: i meas} format
    groups = defaultdict(list)

    # Group currents by rounded voltage
    for r in results[start_idx:end_idx]:
        v = round(r.estimated_lna_voltage, 3)
        i = r.bias_current
        groups[v].append(i)

    print("\nV bias vs I meas: {")
    for v in sorted(groups):
        avg_i = sum(groups[v]) / len(groups[v])
        print(f"  {v:.3f}: {avg_i:1.3e},")
    print("}")

    plt.figure()
    plt.scatter(
        [result.estimated_lna_voltage for result in results[start_idx:end_idx]],
        [result.bias_current * 1000 for result in results[start_idx:end_idx]],
    )
    plt.xlabel("V bias estimated across LNA (V)")
    plt.ylabel("I meas (mA)")
    plt.grid()
    plt.show()


def main():
    log_path = Path(".logdata/souk_lna_bias_control_monitor_2026-02-20_16-05-08.log")
    matches, lines = scan_matches(log_path)
    results = group_sequences(matches, lines)

    print_results(results)


if __name__ == "__main__":
    main()
