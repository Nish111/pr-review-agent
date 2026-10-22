import pytest

from notes_svc.db import connect


@pytest.fixture
def conn():
    c = connect()
    c.execute("INSERT INTO users (id, name, token) VALUES (1, 'priya', 'tok-priya-123')")
    return c
