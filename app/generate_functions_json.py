#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from parse_lims_functions import load_lines, parse_definitions

SOURCE_PATH = ROOT / "limsFunctions_text_format.txt"
OUT_PATH = Path(__file__).resolve().parent / "functions.json"

if not SOURCE_PATH.exists():
    raise FileNotFoundError(f"Source file not found at {SOURCE_PATH}")

lines = load_lines(SOURCE_PATH)
functions = parse_definitions(lines)
rows = [
    {
        "name": func["name"],
        "group_name": func.get("group_name"),
        "purpose": func.get("purpose"),
        "syntax": func.get("syntax"),
        "comments": func.get("comments"),
        "example": func.get("example"),
        "returns": func.get("returns"),
    }
    for func in functions
]

with open(OUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False, indent=2)

print(f"Wrote {len(rows)} functions to {OUT_PATH}")
