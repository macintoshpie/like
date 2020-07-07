from datetime import datetime, timedelta

from flask import g
import sqlite3

from like.config import DATABASE


def datetime_now_str(delta_minutes=0):
    return (datetime.now() + timedelta(minutes=delta_minutes)).isoformat()


def get_db():
    """
    Retrieves or creates a database connection
    """

    def make_dicts(cursor, row):
        return dict(
            (cursor.description[idx][0], value) for idx, value in enumerate(row)
        )

    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = make_dicts  # sqlite3.Row
    return db


def query_db(query, params=None, one=False):
    if params is None:
        params = {}
    with get_db() as con:
        cur = con.execute(query, params)
        rv = cur.fetchall()
        cur.close()
        return (rv[0] if rv else None) if one else rv


def init_db():
    from like import app

    with app.app_context():
        db = get_db()
        with app.open_resource("schema.sql", mode="r") as f:
            db.cursor().executescript(f.read())
        db.commit()
