import sqlite3
import bcrypt

DB_FILE = "users.db"

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# ✅ Get all users and their passwords
cursor.execute("SELECT username, password FROM users")
users = cursor.fetchall()

for username, password in users:
    if isinstance(password, bytes):  # ✅ Decode bytes if needed
        password = password.decode("utf-8")

    # ✅ Check if the password is already hashed
    if password.startswith("$2b$"):  
        print(f"✅ {username}'s password is already hashed.")
        continue  # Skip already hashed passwords

    print(f"🔄 Hashing password for: {username}")

    # ✅ Hash the existing plain text password
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # ✅ Update the database with the hashed password
    cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, username))

conn.commit()
conn.close()
print("✅ All plain text passwords have been rehashed successfully!")