#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "lims_functions.db"
OUT_PATH = Path(__file__).resolve().parent / "functions.json"

if not DB_PATH.exists():
    raise FileNotFoundError(f"Database not found at {DB_PATH}")

with sqlite3.connect(DB_PATH) as conn:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT name, group_name, purpose, syntax, comments, example, returns FROM functions ORDER BY name")
    rows = [dict(row) for row in cur.fetchall()]

with open(OUT_PATH, "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False, indent=2)

print(f"Wrote {len(rows)} functions to {OUT_PATH}")
