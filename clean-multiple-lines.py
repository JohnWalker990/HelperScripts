#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from typing import Tuple, Set

def canonicalize(line: str, ignore_case: bool, strip_ws: bool) -> str:
    """
    <summary>
    Compute a canonical key for deduplication from a single line.
    - Always removes trailing newline characters (\r and \n) to compare content only.
    - Optionally strips leading/trailing whitespace if strip_ws is True.
    - Optionally lowercases the line if ignore_case is True.
    </summary>
    """
    key = line.rstrip("\r\n")
    if strip_ws:
        key = key.strip()
    if ignore_case:
        key = key.lower()
    return key


def dedup_file(input_path: str,
               output_path: str,
               encoding: str = "utf-8",
               ignore_case: bool = False,
               strip_ws: bool = False) -> Tuple[int, int]:
    """
    <summary>
    Deduplicate lines of a text file, keeping the first occurrence of each unique line
    (order-preserving). Writes the cleaned content to output_path.
    Returns a tuple (kept_count, dropped_count).
    </summary>
    """
    seen: Set[str] = set()
    kept, dropped = 0, 0

    # newline="" preserves original per-line endings when reading; and writes exactly what we pass
    with open(input_path, "r", encoding=encoding, errors="replace", newline="") as fin, \
         open(output_path, "w", encoding=encoding, newline="") as fout:

        for line in fin:
            key = canonicalize(line, ignore_case=ignore_case, strip_ws=strip_ws)
            if key in seen:
                dropped += 1
                continue
            seen.add(key)
            fout.write(line)  # write the original line (including its original newline)
            kept += 1

    return kept, dropped


def main():
    """
    <summary>
    CLI entry point that deduplicates lines in a text file and writes them to a new file.
    </summary>
    """
    parser = argparse.ArgumentParser(
        description="Remove duplicate lines from a text file (keep first occurrence; order-preserving)."
    )
    parser.add_argument("input", help="Path to the input text file.")
    parser.add_argument(
        "-o", "--output",
        help="Path to write the cleaned file (default: '<input>.dedup.txt')."
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Text encoding (default: utf-8). Example: cp1252, latin-1."
    )
    parser.add_argument(
        "--ignore-case",
        action="store_true",
        help="Treat lines as equal regardless of case when checking duplicates."
    )
    parser.add_argument(
        "--strip",
        action="store_true",
        help="Strip leading/trailing whitespace before comparing lines."
    )
    args = parser.parse_args()

    out_path = args.output or f"{args.input}.dedup.txt"

    kept, dropped = dedup_file(
        input_path=args.input,
        output_path=out_path,
        encoding=args.encoding,
        ignore_case=args.ignore_case,
        strip_ws=args.strip
    )

    print(f"Input:         {args.input}")
    print(f"Output:        {out_path}")
    print(f"Encoding:      {args.encoding}")
    print(f"Lines kept:    {kept}")
    print(f"Lines removed: {dropped}")


if __name__ == "__main__":
    main()
