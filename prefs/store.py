"""SQLite store for USER SETTINGS ONLY (reading grade / language).

RTS no-storage rule: this database must never hold Slack message content —
only per-user accessibility preferences keyed by Slack user id.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

DEFAULT_GRADE = 6
DEFAULT_LANGUAGE = "English"


@dataclass
class Prefs:
    target_grade: int = DEFAULT_GRADE
    language: str = DEFAULT_LANGUAGE


class PrefsStore:
    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS prefs (
                   user_id     TEXT PRIMARY KEY,
                   target_grade INTEGER NOT NULL DEFAULT 6,
                   language     TEXT    NOT NULL DEFAULT 'English'
               )"""
        )
        self._conn.commit()

    def get(self, user_id: str) -> Prefs:
        row = self._conn.execute(
            "SELECT target_grade, language FROM prefs WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row:
            return Prefs()
        return Prefs(target_grade=row[0], language=row[1])

    def set(self, user_id: str, *, target_grade: int | None = None, language: str | None = None) -> None:
        cur = self.get(user_id)
        grade = target_grade if target_grade is not None else cur.target_grade
        lang = language if language is not None else cur.language
        self._conn.execute(
            """INSERT INTO prefs (user_id, target_grade, language) VALUES (?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET target_grade=excluded.target_grade,
                                                  language=excluded.language""",
            (user_id, grade, lang),
        )
        self._conn.commit()
