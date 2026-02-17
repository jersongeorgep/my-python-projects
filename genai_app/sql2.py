import sqlite3
import bcrypt

DB_FILE = "users.db"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# ✅ Get all users and their passwords
cursor.execute("SELECT username, password FROM users")
users = cursor.fetchall()

for username, password in users:
    if not password.startswith("$2b$"):  # ✅ Only rehash plain text passwords
        print(f"🔄 Hashing password for: {username}")
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, username))

conn.commit()
conn.close()
print("✅ All plain text passwords have been rehashed!")