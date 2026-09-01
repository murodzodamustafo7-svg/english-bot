import sqlite3
from datetime import date

DB_PATH = "bot_data.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        joined_date TEXT
    );

    CREATE TABLE IF NOT EXISTS sent_words (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        word_en TEXT,
        sent_date TEXT,
        answered INTEGER DEFAULT 0,
        correct INTEGER DEFAULT 0
    );
    """)
    conn.commit()
    conn.close()


def add_user(user_id: int, username: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (user_id, username, joined_date) VALUES (?, ?, ?)",
        (user_id, username, date.today().isoformat()),
    )
    conn.commit()
    conn.close()


def get_all_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    rows = cur.fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


def get_sent_words_for_user(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT word_en FROM sent_words WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [r["word_en"] for r in rows]


def record_sent_words(user_id: int, words: list):
    conn = get_conn()
    cur = conn.cursor()
    today = date.today().isoformat()
    for w in words:
        cur.execute(
            "INSERT INTO sent_words (user_id, word_en, sent_date) VALUES (?, ?, ?)",
            (user_id, w["en"], today),
        )
    conn.commit()
    conn.close()


def record_answer(user_id: int, word_en: str, sent_date: str, is_correct: bool):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """UPDATE sent_words SET answered = 1, correct = ?
           WHERE user_id = ? AND word_en = ? AND sent_date = ?""",
        (1 if is_correct else 0, user_id, word_en, sent_date),
    )
    conn.commit()
    conn.close()


def get_score(user_id: int, since_date: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT COUNT(*) as total, SUM(correct) as score
           FROM sent_words WHERE user_id = ? AND sent_date >= ? AND answered = 1""",
        (user_id, since_date),
    )
    row = cur.fetchone()
    conn.close()
    total = row["total"] or 0
    score = row["score"] or 0
    return score, total


def get_total_learned(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """SELECT COUNT(DISTINCT word_en) as cnt FROM sent_words
           WHERE user_id = ? AND correct = 1""",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row["cnt"] or 0
