#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import sys
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import Counter, defaultdict

try:
    from dateutil import parser as du
except ImportError:
    print("This script requires python-dateutil. Install with: pip install python-dateutil")
    sys.exit(1)

DATE_LIKE_RE = re.compile(
    r"""
    ^\s*
    (?P<date>
      \d{1,4}[\-\/\.\s]\d{1,2}[\-\/\.\s]\d{1,4}
      |
      \d{1,2}[\-\/\.\s][A-Za-z]{3,}[\-\/\.\s]\d{2,4}
      |
      [A-Za-z]{3,}\s+\d{1,2},?\s+\d{2,4}
      |
      \d{4}\-\d{1,2}\-\d{1,2}
    )
    (?:[ T]
      \d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)? 
      (?:\s*(?:Z|[+\-]\d{2}:?\d{2}))?
    )?
    \s*$
    """,
    re.VERBOSE,
)

SEP_RE = re.compile(r"[\/\-\.\s]+")

def tokenize_ymd_like(s: str) -> Optional[Tuple[Optional[int], Optional[int], Optional[int]]]:
    parts = SEP_RE.split(s.strip())
    nums = []
    for p in parts:
        if p.isdigit():
            nums.append(int(p))
            if len(nums) == 3:
                break
    if len(nums) >= 3:
        return nums[0], nums[1], nums[2]
    return None

def is_date_like(s: str) -> bool:
    if not s or not s.strip():
        return False
    return bool(DATE_LIKE_RE.match(s.strip()))

def infer_order(samples: List[str]) -> Tuple[Optional[str], Counter]:
    votes = Counter()
    for s in samples:
        toks = tokenize_ymd_like(s)
        if not toks:
            continue
        a, b, c = toks
        if a and a > 31:
            votes["YMD"] += 2
            continue
        if c and c > 31 and a and a <= 31:
            if a > 12:
                votes["DMY"] += 2
            elif b and b > 12:
                votes["MDY"] += 2
            else:
                votes["DMY"] += 1
                votes["MDY"] += 1
            continue
        if a and a > 12:
            votes["DMY"] += 1
        if b and b > 12:
            votes["MDY"] += 1
        if 1000 <= (a or 0) <= 9999 and (b or 0) <= 12 and (c or 0) <= 31:
            votes["YMD"] += 1
    if not votes:
        return None, votes
    best = votes.most_common()
    if len(best) == 1 or best[0][1] > best[1][1]:
        return best[0][0], votes
    return None, votes

def try_parse(s: str, order: Optional[str]) -> Optional[datetime]:
    if not s or not s.strip():
        return None
    kwargs = {}
    if order == "DMY":
        kwargs["dayfirst"] = True
    elif order == "MDY":
        kwargs["dayfirst"] = False
    elif order == "YMD":
        kwargs["yearfirst"] = True
    try:
        return du.parse(s, **kwargs)
    except Exception:
        return None

def column_is_date(samples: List[str]) -> bool:
    non_empty = [s for s in samples if s and s.strip()]
    if not non_empty:
        return False
    like = [s for s in non_empty if is_date_like(s)]
    if len(like) / len(non_empty) < 0.6:
        return False
    for order in (None, "YMD", "DMY", "MDY"):
        ok = sum(1 for s in like if try_parse(s, order) is not None)
        if ok / len(like) >= 0.6:
            return True
    return False

def prompt_for_order(col_name: str, samples: List[str]) -> Optional[str]:
    print(f"\nColumn '{col_name}' is ambiguous. Here are sample values:")
    for s in samples[:10]:
        print(f"  - {s}")
    print("\nChoose date order for this column:")
    print("  1) DMY  (e.g., 31/12/2024)")
    print("  2) MDY  (e.g., 12/31/2024)")
    print("  3) YMD  (e.g., 2024-12-31)")
    print("  4) Skip (leave values unchanged)")
    while True:
        choice = input("Enter 1/2/3/4: ").strip()
        if choice == "1":
            return "DMY"
        if choice == "2":
            return "MDY"
        if choice == "3":
            return "YMD"
        if choice == "4":
            return None
        print("Invalid choice. Please enter 1, 2, 3, or 4.")

def sniff_dialect(fp, sample_bytes=65536):
    start = fp.read(sample_bytes)
    fp.seek(0)
    try:
        dialect = csv.Sniffer().sniff(start.decode(errors="ignore"))
        has_header = csv.Sniffer().has_header(start.decode(errors="ignore"))
    except Exception:
        dialect = csv.excel
        has_header = True
    return dialect, has_header

def sample_column_values(path: str, encoding: str, max_rows: int) -> Tuple[List[str], List[List[str]], csv.Dialect, bool]:
    with open(path, "rb") as fb:
        dialect, has_header = sniff_dialect(fb)
    rows: List[List[str]] = []
    header: List[str] = []
    with open(path, "r", newline="", encoding=encoding, errors="replace") as f:
        reader = csv.reader(f, dialect)
        try:
            first = next(reader)
        except StopIteration:
            return [], [], dialect, True
        header = first
        rows.append(first)
        for i, r in enumerate(reader, start=1):
            rows.append(r)
            if i >= max_rows:
                break
    width = max(len(r) for r in rows) if rows else 0
    for r in rows:
        if len(r) < width:
            r.extend([""] * (width - len(r)))
    if not header or not has_header:
        header = [f"col_{i+1}" for i in range(width)]
    return header, rows[1:] if has_header else rows, dialect, has_header

def decide_columns(header: List[str],
                   rows: List[List[str]],
                   no_prompt: bool,
                   assume_order: Optional[str],
                   force_order: Optional[str]) -> Dict[int, Optional[str]]:
    """
    Return mapping column_index -> chosen order ('DMY'/'MDY'/'YMD') or None to skip.
    - If force_order is set, apply that to every date-like column.
    - Otherwise infer; if ambiguous:
        * if no_prompt: use assume_order (or YMD), else prompt.
    """
    col_samples: Dict[int, List[str]] = defaultdict(list)
    for r in rows:
        for i, v in enumerate(r):
            if v and v.strip():
                col_samples[i].append(v.strip())

    decisions: Dict[int, Optional[str]] = {}
    for i, name in enumerate(header):
        samples = col_samples.get(i, [])
        if not samples:
            continue
        if not column_is_date(samples):
            continue

        if force_order:
            decisions[i] = force_order
            continue

        order, _ = infer_order(samples)
        if order is None:
            # try counts to pick a best
            parsed = {
                "YMD": sum(1 for s in samples if try_parse(s, "YMD") is not None),
                "DMY": sum(1 for s in samples if try_parse(s, "DMY") is not None),
                "MDY": sum(1 for s in samples if try_parse(s, "MDY") is not None),
            }
            best = max(parsed.items(), key=lambda kv: kv[1])
            counts_sorted = sorted(parsed.values(), reverse=True)
            ambiguous = len(samples) > 0 and counts_sorted[1] >= 0.9 * counts_sorted[0]

            if ambiguous:
                if no_prompt:
                    decisions[i] = assume_order or "YMD"
                else:
                    decisions[i] = prompt_for_order(name, samples)
            else:
                decisions[i] = best[0] if best[1] > 0 else ((assume_order or "YMD") if no_prompt else prompt_for_order(name, samples))
        else:
            decisions[i] = order
    return decisions

def format_iso(dt: datetime) -> str:
    if dt.tzinfo:
        return dt.isoformat()
    if dt.hour == 0 and dt.minute == 0 and dt.second == 0 and dt.microsecond == 0:
        return dt.date().isoformat()
    s = dt.isoformat()
    if s.endswith(".000000"):
        s = s[:-7]
    return s

def convert_file(
    input_path: str,
    output_path: str,
    encoding: str = "utf-8",
    sample_rows: int = 200,
    no_prompt: bool = False,
    assume_order: Optional[str] = None,
    force_order: Optional[str] = None,
):
    header, sample_rows_data, dialect, has_header = sample_column_values(input_path, encoding, sample_rows)

    if not header:
        print("Input appears empty. Nothing to do.")
        return

    print(f"Detected delimiter='{dialect.delimiter}' quotechar='{getattr(dialect, 'quotechar', '\"')}' header={has_header}")

    decisions = decide_columns(header, sample_rows_data, no_prompt, assume_order, force_order)
    if not decisions:
        print("No date-like columns detected. Copying input to output unchanged.")
    else:
        picked = {header[i]: v for i, v in decisions.items()}
        print("Date column decisions:")
        for name, order in picked.items():
            if order:
                print(f"  - {name}: {order}")
            else:
                print(f"  - {name}: skipped")

    with open(input_path, "r", newline="", encoding=encoding, errors="replace") as fin, \
         open(output_path, "w", newline="", encoding=encoding) as fout:
        reader = csv.reader(fin, dialect)
        writer = csv.writer(fout, dialect)
        first_row = next(reader, None)
        if first_row is None:
            return
        writer.writerow(first_row)
        for row in reader:
            if len(row) < len(first_row):
                row.extend([""] * (len(first_row) - len(row)))
            out = list(row)
            for idx, order in decisions.items():
                if order is None:
                    continue
                val = row[idx]
                if not val or not val.strip():
                    continue
                dt = try_parse(val, order) or try_parse(val, None)
                if dt is not None:
                    out[idx] = format_iso(dt)
            writer.writerow(out)

def main():
    ap = argparse.ArgumentParser(
        description="Convert date columns in a CSV to ISO-8601, auto-detecting columns and locale."
    )
    ap.add_argument("input", help="Path to input CSV")
    ap.add_argument("-o", "--output", help="Path to output CSV (default: add _iso before extension)")
    ap.add_argument("--encoding", default="utf-8", help="File encoding (default: utf-8)")
    ap.add_argument("--sample-rows", type=int, default=200, help="Rows to sample for detection (default: 200)")

    # NEW: batch-friendly flags
    ap.add_argument("--no-prompt", action="store_true",
                    help="Never prompt; if ambiguous, use --assume (default YMD).")
    ap.add_argument("--assume", choices=["DMY", "MDY", "YMD"],
                    help="Default order to use when a column is ambiguous (used only if --no-prompt).")
    ap.add_argument("--force-order", choices=["DMY", "MDY", "YMD"],
                    help="Force this order for ALL detected date-like columns (skips inference).")

    args = ap.parse_args()

    input_path = args.input
    if args.output:
        output_path = args.output
    else:
        if "." in input_path.rsplit("/", 1)[-1]:
            base, ext = input_path.rsplit(".", 1)
            output_path = f"{base}_iso.{ext}"
        else:
            output_path = f"{input_path}_iso"

    try:
        convert_file(
            input_path=input_path,
            output_path=output_path,
            encoding=args.encoding,
            sample_rows=args.sample_rows,
            no_prompt=args.no_prompt,
            assume_order=args.assume,
            force_order=args.force_order,
        )
        print(f"Done. Wrote: {output_path}")
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
