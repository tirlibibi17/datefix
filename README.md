# CSV Date Normalizer

A Python CLI tool to **normalize date columns in CSV files to ISO-8601 format** (`YYYY-MM-DD` or full timestamp).

## ✨ Features

- **Auto-detect date columns** (based on regex + parsing)
- **Auto-detect locale**:
  - If first token > 12 → assume `DD/MM/YYYY`
  - If second token > 12 → assume `MM/DD/YYYY`
  - If first token looks like a 4-digit year → assume `YYYY/MM/DD`
- **Prompt when ambiguous** → shows sample values and asks you to pick
- **Batch-friendly flags**:
  - `--no-prompt` → never ask, just use fallback
  - `--assume {DMY,MDY,YMD}` → default to this order when ambiguous
  - `--force-order {DMY,MDY,YMD}` → skip detection and force all detected date columns to this order
- Preserves all other columns and formatting

## 📦 Installation

### Option 1 (quickest): run a binary

Grab the binary from the release to the right. There are two binaries built with two different utilities (pyinstaller and nuitka). If one trips your antivirus (e.g. the nuitka one tripped Symantec on my work PC), try the other.

### Option 2: download fix_dates.py from the release and install dependencies

    pip install -r requirements.txt

## 🚀 Usage

Basic (interactive):

    python fix_dates.py input.csv

Output will be written to `input_iso.csv` by default.

    usage: fix_dates.py [-h] [-o OUTPUT] [--encoding ENCODING]
                        [--sample-rows SAMPLE_ROWS]
                        [--no-prompt] [--assume {DMY,MDY,YMD}]
                        [--force-order {DMY,MDY,YMD}]
                        input


    input → Path to CSV file
    -o, --output → Output file (default: input_iso.csv)
    --encoding → Input file encoding (default: utf-8)
    --sample-rows → Number of rows to sample for detection (default: 200)
    --no-prompt → Disable interactive prompts
    --assume → Fallback order when ambiguous (requires --no-prompt)
    --force-order → Force order for all date columns


### Examples

Interactive (asks if ambiguous):

    python fix_dates.py data.csv


Non-interactive, assume DMY when ambiguous:

    python fix_dates.py data.csv --no-prompt --assume DMY


Force MDY for all date-like columns:

    python fix_dates.py data.csv --no-prompt --force-order MDY


Convert with explicit output path:

    python fix_dates.py data.csv -o cleaned.csv


## 📝 Notes

* Timezones and times are preserved (→ full ISO-8601 with offset).
* Pure dates are converted to YYYY-MM-DD.

## 📄 License

MIT License – see LICENSE for details.
