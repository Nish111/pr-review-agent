from notes_svc.auth import check_token
from notes_svc.notes import create_note, get_tags, list_notes, search


def test_token(conn):
    assert check_token(conn, 1, "tok-priya-123")
    assert not check_token(conn, 1, "wrong")
    assert not check_token(conn, 99, "tok-priya-123")


def test_create_and_list_newest_first(conn):
    a = create_note(conn, 1, "first", "a")
    b = create_note(conn, 1, "second", "b")
    assert [n["id"] for n in list_notes(conn, 1)] == [b, a]


def test_pages_do_not_overlap(conn):
    ids = [create_note(conn, 1, f"n{i}", "x") for i in range(5)]
    p1 = [n["id"] for n in list_notes(conn, 1, page=1, per_page=2)]
    p2 = [n["id"] for n in list_notes(conn, 1, page=2, per_page=2)]
    assert not set(p1) & set(p2) and len(p1) == len(p2) == 2 and set(p1) | set(p2) <= set(ids)


def test_search_matches_title_or_body(conn):
    create_note(conn, 1, "groceries", "milk")
    create_note(conn, 1, "work", "buy milk for office")
    create_note(conn, 1, "misc", "nothing")
    assert {n["title"] for n in search(conn, 1, "milk")} == {"groceries", "work"}


def test_get_tags(conn):
    n = create_note(conn, 1, "t", "b")
    conn.execute("INSERT INTO tags VALUES (?, 'home')", (n,))
    assert get_tags(conn, [n]) == {n: ["home"]}
