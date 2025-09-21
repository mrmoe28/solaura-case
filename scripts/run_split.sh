#!/usr/bin/env bash
set -euo pipefail
python3 scripts/split_people.py --csv "data/contacts.csv" --names "config/names_filter.txt" --out "output"