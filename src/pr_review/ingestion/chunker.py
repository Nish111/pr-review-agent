"""Cut one file into chunks whose text is exactly lines start..end (matrix 02: I1, I2, I12)."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from pr_review.ingestion.text import split_lines

WINDOW, OVERLAP = 60, 10          # line windows for non-Python files and module-level code
MAX_FUNCTION = 120                # longer functions are split into labelled windows (I1)


@dataclass(frozen=True)
class Chunk:
    path: str
    start_line: int               # 1-based, inclusive
    end_line: int
    symbol: str                   # "func", "Class.method", "Class", "<module>", "" for plain windows
    kind: str                     # function | class | module | function-part | window
    text: str
    defines: tuple[str, ...] = ()     # every function/class/method name whose `def`/`class` line is in this chunk


def _windows(lo: int, hi: int) -> list[tuple[int, int]]:
    if hi - lo + 1 <= WINDOW:
        return [(lo, hi)]
    out, s = [], lo
    while True:
        e = min(s + WINDOW - 1, hi)
        out.append((s, e))
        if e == hi:
            return out
        s = e - OVERLAP + 1


def _start(node: ast.AST) -> int:
    decos = getattr(node, "decorator_list", [])
    return min([node.lineno] + [d.lineno for d in decos])


def _spans(tree: ast.Module) -> list[tuple[int, int, str, str]]:
    """(start, end, symbol, kind) for functions, classes and methods; big classes are cut into their methods."""
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append((_start(node), node.end_lineno, node.name, "function"))
        elif isinstance(node, ast.ClassDef):
            s, e = _start(node), node.end_lineno
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if e - s + 1 <= MAX_FUNCTION or not methods:
                out.append((s, e, node.name, "class"))
                continue
            first = _start(methods[0])
            out.append((s, first - 1, node.name, "class"))          # header, docstring, class attributes
            for i, m in enumerate(methods):
                m_end = (_start(methods[i + 1]) - 1) if i + 1 < len(methods) else e
                out.append((_start(m), min(m.end_lineno, m_end), f"{node.name}.{m.name}", "function"))
    return out


def chunk_file(path: str, text: str) -> tuple[list[Chunk], bool]:
    """Returns (chunks, parse_fallback). parse_fallback is True when a .py file didn't parse (I2)."""
    lines = split_lines(text)
    if not lines:
        return [], False

    def make(s: int, e: int, symbol: str, kind: str) -> Chunk:
        return Chunk(path, s, e, symbol, kind, "\n".join(lines[s - 1:e]))

    def plain(lo: int, hi: int, symbol: str, kind: str) -> list[Chunk]:
        return [make(s, e, symbol, kind) for s, e in _windows(lo, hi)]

    if not path.endswith(".py"):
        return plain(1, len(lines), "", "window"), False
    try:
        tree = ast.parse("\n".join(lines))
    except (SyntaxError, ValueError):
        return plain(1, len(lines), "", "window"), True

    chunks: list[Chunk] = []
    covered = [False] * (len(lines) + 2)
    for s, e, symbol, kind in _spans(tree):
        if e < s:
            continue
        if kind == "function" and e - s + 1 > MAX_FUNCTION:
            chunks += plain(s, e, symbol, "function-part")
        else:
            chunks.append(make(s, e, symbol, kind))
        for i in range(s, e + 1):
            covered[i] = True
    run_start = None                                        # module-level lines not inside any function/class
    for i in range(1, len(lines) + 2):
        loose = i <= len(lines) and not covered[i]
        if loose and run_start is None:
            run_start = i
        elif not loose and run_start is not None:
            lo, hi = run_start, i - 1
            while lo <= hi and not lines[lo - 1].strip():
                lo += 1
            while hi >= lo and not lines[hi - 1].strip():
                hi -= 1
            if lo <= hi:
                chunks += plain(lo, hi, "<module>", "module")
            run_start = None
    defs = [(n.name, _start(n), n.lineno) for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    chunks = [Chunk(c.path, c.start_line, c.end_line, c.symbol, c.kind, c.text,
                    tuple(dict.fromkeys(name for name, s, line in defs if c.start_line <= line <= c.end_line)))
              for c in chunks]
    return sorted(chunks, key=lambda c: (c.start_line, c.end_line)), False
