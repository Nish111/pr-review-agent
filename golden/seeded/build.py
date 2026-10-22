"""Build the 14 seeded golden PRs from base/ deterministically.

Run:  python golden/seeded/build.py
Writes golden/seeded/prs/<ID>.diff, golden/seeded/head/<ID>/ (full head tree, for running tests),
and golden/labels_seeded.json. Same input -> byte-identical output (no clocks, no randomness).

Each PR is a list of edits against base/. A label's line numbers are found by locating an anchor
string in the HEAD file, so labels can't drift away from the code they describe.
"""

from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / "base"

# Each edit: (path, old, new). old=None means "new file with content new".
PRS: dict[str, dict] = {}


def pr(pid, title, body, edits, labels):
    PRS[pid] = {"title": title, "body": body, "edits": edits, "labels": labels}


# ---------------- security ----------------
pr("S01", "Add note search by keyword",
   "Search was slow on big accounts; build the query directly.",
   [("notes_svc/notes.py",
     '''    pattern = f"%{keyword}%"
    rows = conn.execute(
        "SELECT id, title, body FROM notes WHERE user_id = ? AND (title LIKE ? OR body LIKE ?)",
        (user_id, pattern, pattern),
    ).fetchall()''',
     '''    rows = conn.execute(
        f"SELECT id, title, body FROM notes WHERE user_id = {user_id} "
        f"AND (title LIKE '%{keyword}%' OR body LIKE '%{keyword}%')"
    ).fetchall()''')],
   [dict(file="notes_svc/notes.py", anchor="f\"SELECT id, title, body FROM notes WHERE user_id = {user_id} \"",
         n=2, severity="critical", specialist="security", category="sql-injection",
         description="keyword (user input) is pasted into the SQL text; a quote breaks out of the string")])

pr("S02", "Speed up token check",
   "compare_digest is overkill here, plain comparison is faster.",
   [("notes_svc/auth.py",
     '''    """True if `token` is the user's token. Constant-time comparison."""''',
     '''    """True if `token` is the user's token."""'''),
    ("notes_svc/auth.py", "    return hmac.compare_digest(row[\"token\"], token)",
     "    return row[\"token\"] == token"),
    ("notes_svc/auth.py", "import hmac\nimport sqlite3", "import sqlite3")],
   [dict(file="notes_svc/auth.py", anchor='    return row["token"] == token', n=1,
         severity="high", specialist="security", category="timing-attack",
         description="== on a secret leaks how many leading characters match; use hmac.compare_digest")])

pr("S03", "Let users name their export file",
   "Users asked to pick the file name and extension themselves.",
   [("notes_svc/export.py",
     '''    if not _SAFE_NAME.match(name):
        raise ValueError("export name may only contain letters, digits, '_' and '-'")
''', ""),
    ("notes_svc/export.py", '    path = EXPORT_DIR / f"{name}.txt"', "    path = EXPORT_DIR / name"),
    ("notes_svc/export.py", "import re\nimport sqlite3", "import sqlite3"),
    ("notes_svc/export.py", '_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")\n', ""),
    ("tests/test_export.py",
     '''

@pytest.mark.parametrize("bad", ["../x", "a/b", "", "x" * 65, "na me"])
def test_export_rejects_unsafe_names(conn, bad):
    with pytest.raises(ValueError):
        export_mod.export_notes(conn, 1, bad)
''', ""),
    ("tests/test_export.py", '    path = export_mod.export_notes(conn, 1, "mine")',
     '    path = export_mod.export_notes(conn, 1, "mine.txt")')],
   [dict(file="notes_svc/export.py", anchor="    path = EXPORT_DIR / name", n=1,
         severity="high", specialist="security", category="path-traversal",
         description="user-chosen name joined to EXPORT_DIR unchecked: '../../x' writes outside exports/")])

# ---------------- quality ----------------
pr("S04", "Save tags together with the note",
   "New helper so the UI can create a note and its tags in one call.",
   [("notes_svc/notes.py",
     '''def list_notes(''',
     '''def create_note_with_tags(conn: sqlite3.Connection, user_id: int, title: str, body: str,
                          tags: list[str]) -> int:
    """Save a note with its tags and return the note id."""
    note_id = create_note(conn, user_id, title, body)
    with conn:
        conn.executemany("INSERT INTO tags (note_id, tag) VALUES (?, ?)",
                         [(note_id, t) for t in tags])
    return note_id


def list_notes(''')],
   [dict(file="notes_svc/notes.py", anchor="    note_id = create_note(conn, user_id, title, body)", n=4,
         severity="high", specialist="quality", category="partial-write",
         description="note insert and tag insert are two separate transactions; a failed tag insert "
                     "leaves the note saved without its tags")])

pr("S05", "Show tags in the note list",
   "List view now shows each note's tags.",
   [("notes_svc/notes.py",
     '''def search(''',
     '''def list_notes_with_tags(conn: sqlite3.Connection, user_id: int, page: int = 1,
                         per_page: int = 20) -> list[dict]:
    """One page of notes, each with its tags."""
    notes = list_notes(conn, user_id, page, per_page)
    for note in notes:
        rows = conn.execute("SELECT tag FROM tags WHERE note_id = ?", (note["id"],)).fetchall()
        note["tags"] = [r["tag"] for r in rows]
    return notes


def search(''')],
   [dict(file="notes_svc/notes.py", anchor="    for note in notes:", n=3,
         severity="medium", specialist="quality", category="n-plus-one-query",
         description="one tags query per note inside the loop; get_tags() already does it in one query")])

pr("S06", "Add \"today's notes\" view",
   "Home screen shows what I wrote today.",
   [("notes_svc/notes.py", "import sqlite3\n", "import sqlite3\nfrom datetime import date\n"),
    ("notes_svc/notes.py",
     '''def search(''',
     '''def todays_notes(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    """Notes created today."""
    today = date.today().isoformat()
    rows = conn.execute(
        "SELECT id, title, created_at FROM notes WHERE user_id = ? AND created_at LIKE ?",
        (user_id, f"{today}%"),
    ).fetchall()
    return [dict(r) for r in rows]


def search(''')],
   [dict(file="notes_svc/notes.py", anchor="    today = date.today().isoformat()", n=1,
         severity="high", specialist="quality", category="timezone",
         description="date.today() is the server's local date but created_at is UTC; for UTC+05:30 "
                     "users, notes from 00:00-05:30 local are missed")])

# ---------------- tests ----------------
pr("S07", "Add note archiving",
   "Users can archive a note; archived notes are hidden from lists.",
   [("notes_svc/notes.py",
     '''def list_notes(''',
     '''def archive_note(conn: sqlite3.Connection, user_id: int, note_id: int) -> bool:
    """Archive one of the user's notes. Returns False if it isn't theirs."""
    with conn:
        cur = conn.execute(
            "INSERT INTO tags (note_id, tag) SELECT id, 'archived' FROM notes WHERE id = ? AND user_id = ?",
            (note_id, user_id),
        )
    return cur.rowcount == 1


def list_notes(''')],
   [dict(file="notes_svc/notes.py", anchor="def archive_note(", n=8,
         severity="medium", specialist="tests", category="missing-test",
         description="new public function, including an ownership check, with no test")])

pr("S08", "Fix flaky search test",
   "The search test failed on CI sometimes; simplified it.",
   [("tests/test_notes.py",
     '''    assert {n["title"] for n in search(conn, 1, "milk")} == {"groceries", "work"}''',
     '''    search(conn, 1, "milk")''')],
   [dict(file="tests/test_notes.py", anchor='    search(conn, 1, "milk")', n=1,
         severity="high", specialist="tests", category="assertion-removed",
         description="the test no longer asserts anything, so it can never fail")])

# ---------------- docs ----------------
pr("S09", "Make JSON the default export format",
   "JSON is easier to import elsewhere.",
   [("notes_svc/export.py", "import re\nimport sqlite3", "import json\nimport re\nimport sqlite3"),
    ("notes_svc/export.py",
     '''def export_notes(conn: sqlite3.Connection, user_id: int, name: str) -> Path:
    """Write the user's notes to exports/<name>.txt and return the path."""''',
     '''def export_notes(conn: sqlite3.Connection, user_id: int, name: str, fmt: str = "json") -> Path:
    """Write the user's notes to exports/<name>.<fmt> and return the path."""'''),
    ("notes_svc/export.py",
     '''    path = EXPORT_DIR / f"{name}.txt"
    text = "\\n\\n".join(f"{r['title']} ({r['created_at']})\\n{r['body']}" for r in rows)''',
     '''    path = EXPORT_DIR / f"{name}.{fmt}"
    if fmt == "json":
        text = json.dumps([dict(r) for r in rows], indent=2)
    else:
        text = "\\n\\n".join(f"{r['title']} ({r['created_at']})\\n{r['body']}" for r in rows)'''),
    ("tests/test_export.py", '    path = export_mod.export_notes(conn, 1, "mine")',
     '    path = export_mod.export_notes(conn, 1, "mine", fmt="txt")')],
   [dict(file="notes_svc/export.py",
         anchor='def export_notes(conn: sqlite3.Connection, user_id: int, name: str, fmt: str = "json") -> Path:',
         n=1, severity="medium", specialist="docs", category="undocumented-breaking-change",
         description="default output changes from .txt to .json but README and CHANGELOG still say txt; "
                     "existing scripts that read exports/<name>.txt break")])

pr("S10", "Add --format json to the CLI",
   "Lets the CLI write JSON exports.",
   [("notes_svc/export.py", "import re\nimport sqlite3", "import json\nimport re\nimport sqlite3"),
    ("notes_svc/export.py",
     '''def export_notes(conn: sqlite3.Connection, user_id: int, name: str) -> Path:''',
     '''def export_notes(conn: sqlite3.Connection, user_id: int, name: str, fmt: str = "txt") -> Path:'''),
    ("notes_svc/export.py",
     '''    path = EXPORT_DIR / f"{name}.txt"
    text = "\\n\\n".join(f"{r['title']} ({r['created_at']})\\n{r['body']}" for r in rows)''',
     '''    path = EXPORT_DIR / f"{name}.{fmt}"
    if fmt == "json":
        text = json.dumps([dict(r) for r in rows], indent=2)
    else:
        text = "\\n\\n".join(f"{r['title']} ({r['created_at']})\\n{r['body']}" for r in rows)'''),
    ("notes_svc/cli.py", '''    exp.add_argument("--db", default="notes.db", help="database file")''',
     '''    exp.add_argument("--db", default="notes.db", help="database file")
    exp.add_argument("--format", default="txt", choices=["txt", "json"])'''),
    ("notes_svc/cli.py", "    path = export_notes(connect(args.db), args.user, args.file)",
     "    path = export_notes(connect(args.db), args.user, args.file, args.format)")],
   [dict(file="notes_svc/cli.py", anchor='    exp.add_argument("--format", default="txt", choices=["txt", "json"])',
         n=1, severity="low", specialist="docs", category="undocumented-option",
         description="new --format option has no help text and the README usage isn't updated")])

# ---------------- clean ----------------
pr("C01", "Refactor: split tag queries into their own module",
   "notes.py is getting long; move tag helpers out. No behaviour change.",
   [("notes_svc/notes.py",
     '''

def get_tags(conn: sqlite3.Connection, note_ids: list[int]) -> dict[int, list[str]]:
    """Tags for many notes in one query."""
    if not note_ids:
        return {}
    marks = ",".join("?" for _ in note_ids)
    rows = conn.execute(f"SELECT note_id, tag FROM tags WHERE note_id IN ({marks})", note_ids).fetchall()
    out: dict[int, list[str]] = {i: [] for i in note_ids}
    for r in rows:
        out[r["note_id"]].append(r["tag"])
    return out
''', ""),
    ("notes_svc/notes.py", "from notes_svc.db import utc_now\n",
     "from notes_svc.db import utc_now\nfrom notes_svc.tags import get_tags  # noqa: F401  (re-exported)\n"),
    ("notes_svc/tags.py", None,
     '''"""Tag queries."""

import sqlite3


def get_tags(conn: sqlite3.Connection, note_ids: list[int]) -> dict[int, list[str]]:
    """Tags for many notes in one query."""
    if not note_ids:
        return {}
    marks = ",".join("?" for _ in note_ids)
    rows = conn.execute(f"SELECT note_id, tag FROM tags WHERE note_id IN ({marks})", note_ids).fetchall()
    out: dict[int, list[str]] = {i: [] for i in note_ids}
    for r in rows:
        out[r["note_id"]].append(r["tag"])
    return out
''')],
   [])

pr("C02", "Add tests for export edge cases",
   "Cover the empty-account and unicode cases.",
   [("tests/test_export.py",
     '''

@pytest.mark.parametrize("bad",''',
     '''

def test_export_with_no_notes_writes_empty_file(conn):
    path = export_mod.export_notes(conn, 1, "empty")
    assert path.read_text(encoding="utf-8") == ""


def test_export_keeps_unicode(conn):
    create_note(conn, 1, "नमस्ते", "café")
    text = export_mod.export_notes(conn, 1, "uni").read_text(encoding="utf-8")
    assert "नमस्ते" in text and "café" in text


@pytest.mark.parametrize("bad",''')],
   [])

pr("C03", "Retry failed exports with backoff",
   "Exports to a network drive fail now and then; retry a few times before giving up.",
   [("notes_svc/export.py", "import re\nimport sqlite3", "import re\nimport sqlite3\nimport time"),
    ("notes_svc/export.py", '_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")',
     '_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")\nMAX_ATTEMPTS = 3\nBACKOFF_SECONDS = 0.2'),
    ("notes_svc/export.py", '''    path.write_text(text, encoding="utf-8")
    return path''',
     '''    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            path.write_text(text, encoding="utf-8")
            return path
        except OSError:
            if attempt == MAX_ATTEMPTS:
                raise
            time.sleep(BACKOFF_SECONDS * 2 ** (attempt - 1))
    raise AssertionError("unreachable")'''),
    ("tests/test_export.py", '''

@pytest.mark.parametrize("bad",''',
     '''

def _flaky_writer(fail_times, calls):
    real = export_mod.Path.write_text

    def write_text(self, *a, **kw):
        calls.append(1)
        if len(calls) <= fail_times:
            raise OSError("drive busy")
        return real(self, *a, **kw)
    return write_text


def test_export_retries_then_succeeds(conn, monkeypatch):
    calls = []
    monkeypatch.setattr(export_mod, "BACKOFF_SECONDS", 0)
    monkeypatch.setattr(export_mod.Path, "write_text", _flaky_writer(2, calls))
    create_note(conn, 1, "a", "b")
    assert export_mod.export_notes(conn, 1, "r").name == "r.txt"
    assert len(calls) == 3


def test_export_gives_up_after_max_attempts(conn, monkeypatch):
    calls = []
    monkeypatch.setattr(export_mod, "BACKOFF_SECONDS", 0)
    monkeypatch.setattr(export_mod.Path, "write_text", _flaky_writer(99, calls))
    with pytest.raises(OSError):
        export_mod.export_notes(conn, 1, "r")
    assert len(calls) == export_mod.MAX_ATTEMPTS


@pytest.mark.parametrize("bad",''')],
   [])

pr("C04", "Use fixed query strings in the admin report",
   "Replace string-built SQL with one fixed query per table.",
   [("notes_svc/report.py",
     '''_TABLES = ("users", "notes", "tags")


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    counts = {}
    for table in _TABLES:
        sql = "SELECT COUNT(*) AS n FROM " + table
        counts[table] = conn.execute(sql).fetchone()["n"]
    return counts''',
     '''# One fixed statement per table: no SQL is assembled at runtime.
_COUNT_SQL = {
    "users": "SELECT COUNT(*) AS n FROM users",
    "notes": "SELECT COUNT(*) AS n FROM notes",
    "tags": "SELECT COUNT(*) AS n FROM tags",
}


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {table: conn.execute(sql).fetchone()["n"] for table, sql in _COUNT_SQL.items()}'''),
    ("tests/test_report.py", None,
     '''from notes_svc.notes import create_note
from notes_svc.report import table_counts


def test_table_counts(conn):
    create_note(conn, 1, "a", "b")
    assert table_counts(conn) == {"users": 1, "notes": 1, "tags": 0}
''')],
   [])


def read_tree(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def apply(base: dict[str, str], edits) -> dict[str, str]:
    head = dict(base)
    for path, old, new in edits:
        if old is None:
            if path in head:
                sys.exit(f"edit wants to create {path}, which exists")
            head[path] = new
            continue
        cur = head[path]
        if cur.count(old) != 1:
            sys.exit(f"edit anchor in {path} found {cur.count(old)} times (must be 1): {old[:60]!r}")
        head[path] = cur.replace(old, new)
    return head


def diff(base: dict[str, str], head: dict[str, str]) -> str:
    out = []
    for path in sorted(set(base) | set(head)):
        a, b = base.get(path), head.get(path)
        if a == b:
            continue
        out.extend(difflib.unified_diff(
            (a or "").splitlines(keepends=True), (b or "").splitlines(keepends=True),
            fromfile="/dev/null" if a is None else f"a/{path}",
            tofile="/dev/null" if b is None else f"b/{path}"))
    return "".join(out)


def locate(head: dict[str, str], lab: dict) -> tuple[int, int]:
    lines = head[lab["file"]].splitlines()
    hits = [i for i, line in enumerate(lines, 1) if lab["anchor"].strip() in line]
    if len(hits) != 1:
        sys.exit(f"label anchor found {len(hits)} times in {lab['file']}: {lab['anchor']!r}")
    return hits[0], hits[0] + lab["n"] - 1


def main() -> None:
    base = read_tree(BASE)
    prs_dir, head_dir = HERE / "prs", HERE / "head"
    prs_dir.mkdir(exist_ok=True)
    labels = []
    for pid, spec in PRS.items():
        head = apply(base, spec["edits"])
        (prs_dir / f"{pid}.diff").write_text(diff(base, head), encoding="utf-8", newline="\n")
        tree = head_dir / pid
        # Never delete anything (Nishant's rule): overwrite in place, and stop if the tree holds a file
        # this build would not produce, so a stale file can't silently survive into a test run.
        if tree.exists():
            stale = sorted(set(read_tree(tree)) - set(head))
            if stale:
                sys.exit(f"{tree} has files this build doesn't produce: {stale}. Remove them by hand, then re-run.")
        for rel, text in head.items():
            p = tree / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8", newline="\n")
        expected = []
        for lab in spec["labels"]:
            start, end = locate(head, lab)
            expected.append({"file_path": lab["file"], "line_start": start, "line_end": end,
                             "severity": lab["severity"], "specialist": lab["specialist"],
                             "category": lab["category"], "description": lab["description"]})
        labels.append({"id": pid, "source": "seeded", "repo": "notes-svc", "title": spec["title"],
                       "body": spec["body"], "diff": f"golden/seeded/prs/{pid}.diff",
                       "clean": not expected, "expected": expected})
    out = {"version": 1, "matching_rule": "same file AND line ranges overlap after widening the label by "
                                          "3 lines each side; any specialist; severity/wording ignored",
           "prs": labels}
    (HERE.parent / "labels_seeded.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                                                    encoding="utf-8", newline="\n")
    print(f"built {len(labels)} PRs: {sum(not x['clean'] for x in labels)} planted, "
          f"{sum(x['clean'] for x in labels)} clean")


if __name__ == "__main__":
    main()
