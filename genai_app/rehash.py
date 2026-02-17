import sqlite3
import bcrypt

DB_FILE = "users.db"  # Ensure this matches your database file

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# ✅ Get all users and their passwords
cursor.execute("SELECT username, password FROM users")
users = cursor.fetchall()

for username, password in users:
    # ✅ Ensure password is a string (decode if stored as bytes)
    if isinstance(password, bytes):
        password = password.decode("utf-8")

    # ✅ Skip already hashed passwords (bcrypt hashes start with "$2b$")
    if password.startswith("$2b$"):
        print(f"✅ {username} already has a hashed password.")
        continue
    
    print(f"🔄 Hashing password for: {username}")

    # ✅ Hash the existing plain text password
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # ✅ Update the database with the hashed password
    cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, username))

conn.commit()
conn.close()
print("✅ All passwords have been rehashed successfully!")
