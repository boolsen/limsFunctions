#!/usr/bin/env python3
import argparse
import os
import re
import sqlite3
import sys
from typing import Dict, List, Optional, Tuple

SOURCE_FILE = "limsFunctions_text_format.txt"
DB_FILE = "lims_functions.db"

SECTION_LABELS = ["Purpose", "Syntax", "Comments", "Example", "Returns"]


def normalize_line(line: str) -> str:
    return line.rstrip("\n\r")


def load_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return [normalize_line(line) for line in fh]


def parse_function_groups(lines: List[str]) -> Dict[str, str]:
    groups: Dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line == "Function":
            i += 1
            while i + 1 < len(lines):
                name = lines[i].strip()
                group = lines[i + 1].strip()
                if not name or not group or name == "Function" or group == "Functional Group":
                    break
                if name and group:
                    groups[name] = group
                i += 2
            continue
        i += 1
    return groups


def find_function_name_before(lines: List[str], index: int) -> Optional[str]:
    for j in range(index - 1, -1, -1):
        candidate = lines[j].strip()
        if not candidate:
            continue
        normalized = candidate.rstrip(":")
        if normalized in SECTION_LABELS or normalized == "Function":
            continue
        return candidate
    return None


def split_definitions(lines: List[str]) -> List[Tuple[int, int]]:
    indices = [i for i, line in enumerate(lines) if line.strip() == "Purpose:"]
    boundaries: List[Tuple[int, int]] = []
    for n, start in enumerate(indices):
        end = indices[n + 1] if n + 1 < len(indices) else len(lines)
        boundaries.append((start, end))
    return boundaries


def extract_section_text(section: str, lines: List[str], start: int, end: int) -> str:
    content_lines: List[str] = []
    in_section = False
    normalized_section = section.rstrip(":")

    def next_nonempty_is_purpose(index: int) -> bool:
        for j in range(index + 1, min(end + 1, len(lines))):
            if lines[j].strip() == "":
                continue
            return lines[j].strip() == "Purpose:"
        return False

    def is_new_section_header(text: str) -> bool:
        stripped = text.strip()
        if stripped == "Function":
            return True
        if re.match(r"^\d+(?:\.\d+)*\s+\S", stripped):
            return True
        return False

    for i in range(start, end):
        text = lines[i]
        label = text.strip().rstrip(":")
        if label == normalized_section:
            in_section = True
            continue
        if in_section and (label in SECTION_LABELS or next_nonempty_is_purpose(i) or is_new_section_header(text)):
            break
        if in_section:
            content_lines.append(text)
    # Trim leading/trailing blank lines.
    while content_lines and content_lines[0].strip() == "":
        content_lines.pop(0)
    while content_lines and content_lines[-1].strip() == "":
        content_lines.pop()
    return "\n".join(content_lines).strip()


def parse_definitions(lines: List[str]) -> List[Dict[str, Optional[str]]]:
    groups = parse_function_groups(lines)
    definitions = []
    for start, end in split_definitions(lines):
        name = find_function_name_before(lines, start)
        if not name:
            continue
        function_data: Dict[str, Optional[str]] = {
            "name": name,
            "group_name": groups.get(name),
            "purpose": None,
            "syntax": None,
            "comments": None,
            "example": None,
            "returns": None,
        }
        for section in SECTION_LABELS:
            text = extract_section_text(section, lines, start, end)
            if text:
                function_data[section.lower()] = text
        definitions.append(function_data)
    return definitions


def make_db(db_path: str, functions: List[Dict[str, Optional[str]]]) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE functions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            group_name TEXT,
            purpose TEXT,
            syntax TEXT,
            comments TEXT,
            example TEXT,
            returns TEXT
        )
        """
    )
    cur.execute(
        "CREATE VIRTUAL TABLE functions_fts USING fts5(name, group_name, purpose, syntax, comments, example, returns, content='functions', content_rowid='id')"
    )

    for func in functions:
        cur.execute(
            "INSERT INTO functions (name, group_name, purpose, syntax, comments, example, returns) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                func["name"],
                func.get("group_name"),
                func.get("purpose"),
                func.get("syntax"),
                func.get("comments"),
                func.get("example"),
                func.get("returns"),
            ),
        )
    cur.execute(
        "INSERT INTO functions_fts(functions_fts) VALUES('rebuild')"
    )
    conn.commit()
    conn.close()


def ensure_db(source_path: str, db_path: str) -> None:
    if os.path.exists(db_path):
        return
    build_database(source_path, db_path)


def build_database(source_path: str, db_path: str) -> None:
    lines = load_lines(source_path)
    functions = parse_definitions(lines)
    make_db(db_path, functions)
    print(f"Built database '{db_path}' with {len(functions)} function definitions.")


def format_function_row(row: sqlite3.Row) -> str:
    parts = [f"Function: {row['name']}" ]
    if row["group_name"]:
        parts.append(f"Group: {row['group_name']}")
    for section in ["purpose", "syntax", "comments", "example", "returns"]:
        value = row[section]
        if value:
            parts.append(f"\n{section.capitalize()}:\n{value}")
    return "\n".join(parts)


def query_by_name(conn: sqlite3.Connection, name: str) -> List[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM functions WHERE name = ? COLLATE NOCASE", (name,))
    return cur.fetchall()


def query_by_keyword(conn: sqlite3.Connection, keyword: str) -> List[sqlite3.Row]:
    cur = conn.cursor()
    expr = " OR ".join(
        [f"{field}:\"{keyword}\"" for field in ["name", "group_name", "purpose", "syntax", "comments", "example", "returns"]]
    )
    try:
        cur.execute(
            "SELECT functions.* FROM functions_fts JOIN functions ON functions_fts.rowid = functions.id WHERE functions_fts MATCH ?",
            (expr,),
        )
        return cur.fetchall()
    except sqlite3.OperationalError:
        # Fallback to LIKE search if FTS is unavailable.
        term = f"%{keyword}%"
        cur.execute(
            "SELECT * FROM functions WHERE name LIKE ? OR group_name LIKE ? OR purpose LIKE ? OR syntax LIKE ? OR comments LIKE ? OR example LIKE ? OR returns LIKE ?",
            (term, term, term, term, term, term, term),
        )
        return cur.fetchall()


def list_functions(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute("SELECT name, group_name FROM functions ORDER BY name")
    return cur.fetchall()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse limsFunctions_text_format.txt into a queryable SQLite database."
    )
    parser.add_argument(
        "--source",
        default=SOURCE_FILE,
        help="Path to limsFunctions_text_format.txt",
    )
    parser.add_argument(
        "--db",
        default=DB_FILE,
        help="Path to output SQLite database file.",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Build the SQLite database from the source text file.",
    )
    parser.add_argument(
        "--name",
        help="Query by exact function name.",
    )
    parser.add_argument(
        "--keyword",
        help="Query by keyword across function name, purpose, syntax, comments, example, and returns.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all parsed function names and groups.",
    )

    args = parser.parse_args(argv)

    if args.build:
        build_database(args.source, args.db)
        return 0

    ensure_db(args.source, args.db)
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    if args.list:
        rows = list_functions(conn)
        for row in rows:
            print(f"{row['name']} ({row['group_name'] or 'Unknown'})")
        return 0

    if args.name:
        rows = query_by_name(conn, args.name)
        if not rows:
            print(f"No function found with name '{args.name}'")
            return 1
        print(format_function_row(rows[0]))
        return 0

    if args.keyword:
        rows = query_by_keyword(conn, args.keyword)
        if not rows:
            print(f"No functions found matching keyword '{args.keyword}'")
            return 1
        for row in rows:
            print(format_function_row(row))
            print("\n" + "-" * 80 + "\n")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
