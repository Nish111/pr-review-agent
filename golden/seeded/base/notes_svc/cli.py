"""Command line: python -m notes_svc.cli export --user 1 --file mynotes"""

import argparse

from notes_svc.db import connect
from notes_svc.export import export_notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notes_svc")
    sub = parser.add_subparsers(dest="cmd", required=True)
    exp = sub.add_parser("export", help="export a user's notes to exports/<file>.txt")
    exp.add_argument("--user", type=int, required=True, help="user id")
    exp.add_argument("--file", required=True, help="export name (letters, digits, _ and -)")
    exp.add_argument("--db", default="notes.db", help="database file")
    args = parser.parse_args(argv)
    path = export_notes(connect(args.db), args.user, args.file)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
