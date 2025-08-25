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

Clone the repo and install dependencies:

```bash
git clone https://github.com/yourname/csv-date-normalizer.git
cd csv-date-normalizer
pip install -r requirements.txt

## 🚀 Usage

Basic (interactive):

python csv_dates_to_iso.py input.csv

Output will be written to input_iso.csv by default.

Options

    usage: csv_dates_to_iso.py [-h] [-o OUTPUT] [--encoding ENCODING]
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
