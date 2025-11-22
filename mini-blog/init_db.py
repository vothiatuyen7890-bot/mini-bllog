import sqlite3
conn = sqlite3.connect("database.db")
conn.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
conn.execute("CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY, title TEXT, content TEXT)")
conn.commit()
print("Database OK")