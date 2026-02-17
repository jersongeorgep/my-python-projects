import sqlite3
import bcrypt

def hash_password(password):
    salt = bcrypt.gensalt()  # Generates a new salt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password

def update_user_password(username, new_password):
    conn = sqlite3.connect("users.db")  # Replace with your actual database file
    cursor = conn.cursor()
    
    # Hash the new password
    hashed_password = hash_password(new_password)
    
    # Update the password in the database
    cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_password, username))
    conn.commit()
    conn.close()
    
    print(f"Password updated for {username}")

# Update the admin password
update_user_password("admin", "Pinakine1#")
