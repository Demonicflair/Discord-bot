import sqlite3

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS levels (
user_id INTEGER,
guild_id INTEGER,
xp INTEGER,
level INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS warnings (
user_id INTEGER,
guild_id INTEGER,
count INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS whitelist (
user_id INTEGER,
guild_id INTEGER
)
""")

conn.commit()

def add_xp(u,g,amt):
    cursor.execute("SELECT xp,level FROM levels WHERE user_id=? AND guild_id=?", (u,g))
    d=cursor.fetchone()
    if not d:
        xp,level=amt,1
    else:
        xp,level=d[0]+amt,d[1]

    leveled=False
    if xp>=100:
        xp=0; level+=1; leveled=True

    cursor.execute("DELETE FROM levels WHERE user_id=? AND guild_id=?", (u,g))
    cursor.execute("INSERT INTO levels VALUES (?,?,?,?)",(u,g,xp,level))
    conn.commit()
    return level,leveled

def get_lb(g):
    cursor.execute("SELECT user_id,level FROM levels WHERE guild_id=? ORDER BY level DESC LIMIT 10",(g,))
    return cursor.fetchall()

def add_warn(u,g):
    cursor.execute("SELECT count FROM warnings WHERE user_id=? AND guild_id=?", (u,g))
    d=cursor.fetchone()
    c=d[0]+1 if d else 1

    cursor.execute("DELETE FROM warnings WHERE user_id=? AND guild_id=?", (u,g))
    cursor.execute("INSERT INTO warnings VALUES (?,?,?)",(u,g,c))
    conn.commit()
    return c

def add_whitelist(u,g):
    cursor.execute("INSERT INTO whitelist VALUES (?,?)",(u,g))
    conn.commit()

def is_whitelisted(u,g):
    cursor.execute("SELECT * FROM whitelist WHERE user_id=? AND guild_id=?", (u,g))
    return cursor.fetchone()!=None