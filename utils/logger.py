import sqlite3

db = sqlite3.connect("logs.db", check_same_thread=False)
cursor = db.cursor()

# =========================
# TABLES
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS log_channels(
    guild_id INTEGER PRIMARY KEY,
    mod_log INTEGER,
    bot_log INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS log_settings(
    guild_id INTEGER,
    log_type TEXT,
    enabled INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs_data(
    guild_id INTEGER,
    user_id INTEGER,
    type TEXT,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

db.commit()

# =========================
# CHANNEL FETCH
# =========================
def get_logs(guild_id):
    cursor.execute("SELECT mod_log, bot_log FROM log_channels WHERE guild_id=?", (guild_id,))
    return cursor.fetchone()

# =========================
# SAVE LOG
# =========================
def save_log(guild_id, user_id, log_type, content):
    cursor.execute(
        "INSERT INTO logs_data(guild_id, user_id, type, content) VALUES (?, ?, ?, ?)",
        (guild_id, user_id, log_type, content)
    )
    db.commit()

# =========================
# SEARCH
# =========================
def search_logs_db(guild_id, query, log_type=None):
    if log_type:
        cursor.execute(
            "SELECT * FROM logs_data WHERE guild_id=? AND type=? AND content LIKE ? ORDER BY timestamp DESC LIMIT 10",
            (guild_id, log_type, f"%{query}%")
        )
    else:
        cursor.execute(
            "SELECT * FROM logs_data WHERE guild_id=? AND content LIKE ? ORDER BY timestamp DESC LIMIT 10",
            (guild_id, f"%{query}%")
        )
    return cursor.fetchall()

# =========================
# FILTER SYSTEM
# =========================
def is_log_enabled(guild_id, log_type):
    cursor.execute(
        "SELECT enabled FROM log_settings WHERE guild_id=? AND log_type=?",
        (guild_id, log_type)
    )
    r = cursor.fetchone()
    return r is None or r[0] == 1

def set_log(guild_id, log_type, state):
    cursor.execute(
        "DELETE FROM log_settings WHERE guild_id=? AND log_type=?",
        (guild_id, log_type)
    )
    cursor.execute(
        "INSERT INTO log_settings VALUES (?, ?, ?)",
        (guild_id, log_type, int(state))
    )
    db.commit()
