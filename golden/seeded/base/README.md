# notes-svc

A small notes service: users authenticate with a token, save notes, tag them, search them and export them.

## Usage

    python -m notes_svc.cli export --user 1 --file mynotes

Writes `exports/mynotes.txt`. Export format: plain text, one note per block.

## API

- `create_note(conn, user_id, title, body)`: save a note; returns its id.
- `list_notes(conn, user_id, page=1, per_page=20)`: one page of notes, newest first.
- `search(conn, user_id, keyword)`: notes whose title or body contains `keyword`.
- `export_notes(conn, user_id, name)`: write the user's notes to `exports/<name>.txt`.
