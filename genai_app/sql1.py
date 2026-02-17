import sqlite3

DB_FILE = "users.db"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# ✅ Get all users and their passwords
cursor.execute("SELECT username, password FROM users")
users = cursor.fetchall()

for username, password in users:
    print(f"User: {username}, Password: {password}")  # ✅ Check stored passwords

conn.close()