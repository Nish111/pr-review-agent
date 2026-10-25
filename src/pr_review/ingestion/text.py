"""One line-splitting rule and one identifier rule, used by the index, retrieval and tests alike (I12, R1, R3)."""

from __future__ import annotations

import builtins
import keyword
import re

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")
STOP = frozenset(keyword.kwlist) | frozenset(dir(builtins)) | {"self", "cls", "args", "kwargs", "None", "True", "False"}


def split_lines(text: str) -> list[str]:
    """Lines as git and GitHub count them: split on \\n only, drop a trailing \\r, no phantom last line.
    (str.splitlines also splits on form feeds and other characters, which makes line numbers drift: I12.)"""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [ln[:-1] if ln.endswith("\r") else ln for ln in lines]


def identifiers(text: str) -> list[str]:
    """Every identifier in the text, in order of first appearance, each once."""
    return list(dict.fromkeys(_IDENT.findall(text)))


def parts(name: str) -> list[str]:
    """verify_token -> [verify, token]; parseHTTPHeader -> [parse, HTTP, Header] (lower-cased)."""
    out = []
    for piece in name.split("_"):
        out += [p.lower() for p in _CAMEL.findall(piece)]
    return [p for p in out if p]


def ident_field(text: str) -> str:
    """What the keyword lane indexes for a chunk: each identifier whole, plus its parts (R1). No stemming."""
    words: list[str] = []
    for name in identifiers(text):
        words.append(name.lower())
        ps = parts(name)
        if len(ps) > 1:
            words += ps
    return " ".join(words)
