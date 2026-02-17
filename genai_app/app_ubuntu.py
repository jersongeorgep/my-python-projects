from flask import Flask, request, jsonify, send_file, stream_with_context, Response, session
from flask_session import Session  # ✅ Import Flask-Session
import multiprocessing
import os
import json
import tempfile
import base64
import time
import random
import sqlite3
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
import vertexai
import bcrypt
import pandas as pd
from flask_cors import CORS
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)
# ✅ Configure Flask session to persist data
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"  # Uses file-based session storage
Session(app)  # ✅ Initialize session

DB_FILE = "users.db"
load_dotenv()

# Google Cloud project details
project = os.getenv("GENAI_PROJECT")
location = os.getenv("GENAI_LOCATION")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "peppy-linker-332510-c7733d076051.json"
app.config['SECRET_KEY'] = 'Genaiapplication'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# def init_db():
#     with sqlite3.connect(DB_FILE) as conn:
#         cursor = conn.cursor()
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS users (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 username TEXT UNIQUE NOT NULL,
#                 password TEXT NOT NULL
#             )
#         """)
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS extraction_history (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 username TEXT NOT NULL,
#                 document_name TEXT NOT NULL,
#                 total_rows INTEGER NOT NULL,
#                 total_time REAL NOT NULL,
#                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
#             )
#         """)
#         conn.commit()

#         # Insert default admin user
#         try:
#             cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", "admin123"))
#             conn.commit()
#         except sqlite3.IntegrityError:
#             pass  # Admin already exists

# init_db()

def init_db():
    """Initialize the database if it doesn't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # ✅ Create users table for authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)

        # ✅ Create extraction history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extraction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                document_name TEXT NOT NULL,
                total_rows INTEGER NOT NULL,
                total_time REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ✅ Create removed users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS removed_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                removed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

        # ✅ Ensure admin user exists in `users` table
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        admin_exists = cursor.fetchone()[0]

        if not admin_exists:
            hashed_password = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", hashed_password))
            conn.commit()

        print("✅ Database initialized successfully!")

# ✅ Run this at startup
init_db()




def hash_password(password):
    """Generate a hashed password using bcrypt."""
    salt = bcrypt.gensalt()  # Generates a new salt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode("utf-8")  # Decode to store in DB
    return hashed_password



def authenticate_user(username, password):
    """Authenticate users using hashed passwords stored in the `users` table."""
    try:
        conn = get_db()
        cursor = conn.cursor()

        # ✅ Fetch stored hashed password
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user:
            stored_hashed_password = user[0]

            # ✅ Ensure stored password is a string (decode if necessary)
            if isinstance(stored_hashed_password, bytes):
                stored_hashed_password = stored_hashed_password.decode("utf-8")

            # ✅ Ensure it's a hashed password (should start with "$2b$")
            if not stored_hashed_password.startswith("$2b$"):
                print(f"⚠️ Warning: Password for {username} is not hashed correctly!")
                return False

            # ✅ Compare the provided password with the stored hashed password
            if bcrypt.checkpw(password.encode("utf-8"), stored_hashed_password.encode("utf-8")):
                return True

        return False  # Login failed

    except Exception as e:
        print(f"Error during authentication: {e}")
        return False




def save_extraction_history(username, document_name, total_rows, total_time):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO extraction_history (username, document_name, total_rows, total_time)
        VALUES (?, ?, ?, ?)
    """, (username, document_name, total_rows, total_time))
    conn.commit()
    conn.close()

def extract_text_from_image(image_path, prompt, page_number):
    max_retries = 10  # Maximum retry attempts
    backoff_factor = 2  # Exponential backoff (2, 4, 8, 16 sec)
    max_wait_time = 30  # **Maximum time allowed (30 seconds)**
    start_time = time.time()

    extracted_data = []  # **Store extracted results**
    skipped_pages = []  # **Track skipped pages**
    timeout_reached = False  # **Flag if timeout occurs**

    try:
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode("utf-8")

        vertexai.init(project=project, location=location)
        image_part = Part.from_data(mime_type="image/png", data=base64.b64decode(encoded_image))
        model = GenerativeModel("gemini-1.5-flash-002")
        chat = model.start_chat()

        for attempt in range(max_retries):
            elapsed_time = time.time() - start_time

            if elapsed_time > max_wait_time:
                print(f"Timeout reached ({max_wait_time} sec). Skipping Page {page_number}...")
                skipped_pages.append(page_number)  # ✅ Mark this page as skipped
                timeout_reached = True
                break  # **Stop trying this page**

            try:
                response = chat.send_message(
                    [image_part, prompt],
                    generation_config={"max_output_tokens": 8192, "temperature": 1, "top_p": 0.95, "response_mime_type": "application/json"},
                    safety_settings = [
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=SafetySetting.HarmBlockThreshold.OFF
                ),
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=SafetySetting.HarmBlockThreshold.OFF
                ),
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=SafetySetting.HarmBlockThreshold.OFF
                ),
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=SafetySetting.HarmBlockThreshold.OFF
                ),
            ]
                )

                response_text = response.text.strip().strip("```json").strip("```")

                if response_text:
                    extracted_data = json.loads(response_text)  # **Store results**
                    return {
                        "extracted_data": extracted_data,
                        "skipped_pages": skipped_pages,  # **Pages that were not processed**
                        "timeout": timeout_reached
                    }

            except Exception as e:
                if "429" in str(e):
                    wait_time = backoff_factor ** attempt  # Exponential wait (2, 4, 8 sec)
                    print(f"Rate limit hit (429), retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"Error extracting text from Page {page_number}: {e}")
                    break  # **Skip this page if another error occurs**

        print(f"Max retries exceeded for Page {page_number}. Skipping...")
        skipped_pages.append(page_number)  # **Mark page as skipped**
        return {
            "extracted_data": extracted_data,
            "skipped_pages": skipped_pages,
            "timeout": timeout_reached
        }

    except Exception as e:
        print(f"Critical error extracting text from Page {page_number}: {e}")
        return {
            "extracted_data": [],
            "skipped_pages": [page_number],
            "timeout": timeout_reached
        }


@app.route('/login', methods=['POST'])
def login():
    """Login endpoint that validates users from `users` table."""
    data = request.get_json()

    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Missing required parameters"}), 400

    username = data["username"]
    password = data["password"]

    if not authenticate_user(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    # ✅ Set session for logged-in user
    session['username'] = username

    return jsonify({
        "message": "Login successful!",
        "username": username
    })


@app.route('/change_password', methods=['POST'])
def change_password():
    """Allow users to change their password using only their current credentials (like the original structure)."""

    # ✅ Ensure required form parameters are present
    if "current_password" not in request.form or "new_password" not in request.form:
        return jsonify({"error": "Missing required parameters"}), 400

    current_password = request.form["current_password"]
    new_password = request.form["new_password"]

    conn = get_db()
    cursor = conn.cursor()

    # ✅ Fetch the user who has this password
    cursor.execute("SELECT username, password FROM users")
    users = cursor.fetchall()

    user_found = None
    for user in users:
        stored_hashed_password = user["password"]
        if isinstance(stored_hashed_password, bytes):
            stored_hashed_password = stored_hashed_password.decode("utf-8")

        # ✅ Check if the entered `current_password` matches any stored password
        if bcrypt.checkpw(current_password.encode("utf-8"), stored_hashed_password.encode("utf-8")):
            user_found = user["username"]
            break  # ✅ Exit loop once a match is found

    # ✅ If no user found with this password, return error
    if not user_found:
        conn.close()
        return jsonify({"error": "Current password is incorrect"}), 401

    # ✅ Hash the new password before storing it
    hashed_new_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # ✅ Update password in the database
    cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_new_password, user_found))
    conn.commit()
    conn.close()

    return jsonify({"message": "Password changed successfully!"}), 200



# Logout endpoint to clear the session
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)  # Remove 'username' from session
    return jsonify({"message": "Logged out successfully!"})

@app.route("/create_user", methods=["POST"])
def create_user():
    """Admin creates a new user with a hashed password."""
    data = request.json
    admin_username = data.get("admin_username")
    admin_password = data.get("admin_password")
    new_username = data.get("new_username")
    new_password = data.get("new_password")

    # ✅ Authenticate admin
    if admin_username != "admin" or not authenticate_user(admin_username, admin_password):
        return jsonify({"error": "Only admin can create users"}), 403

    # ✅ Ensure username and password are provided
    if not new_username or not new_password:
        return jsonify({"error": "New username and password required"}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()

        # ✅ Use the fixed `hash_password()` function
        hashed_password = hash_password(new_password)

        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_username, hashed_password))
        conn.commit()
        return jsonify({"message": "User created successfully"}), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400

    finally:
        conn.close()



def save_extracted_data_to_excel(extracted_data, filename):
    df = pd.DataFrame(extracted_data)
    excel_path = os.path.join(tempfile.gettempdir(), filename)
    df.to_excel(excel_path, index=False)
    print(f"Excel file saved at: {excel_path}")
    return excel_path

@app.route("/download_excel", methods=["GET"])
def download_excel():
    filename = request.args.get("filename")
    file_path = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404



def process_pdf(pdf_path, prompt, username, queue, total_pages_global):
    document_name = os.path.basename(pdf_path)
    print(f"Started processing: {document_name}", flush=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            images = convert_from_path(pdf_path, output_folder=temp_dir, fmt="jpeg")
            total_pages = len(images)  
            all_data = []
            skipped_pages = []
            start_time = time.time()

            for idx, image in enumerate(images):
                page_number = idx + 1
                image_path = os.path.join(temp_dir, f"page_{page_number}.jpg")
                image.save(image_path, "JPEG")

                # ✅ Extract text
                extraction_result = extract_text_from_image(image_path, prompt, page_number)

                if extraction_result["extracted_data"]:
                    for item in extraction_result["extracted_data"]:
                        item["page_number"] = page_number
                        item["document_name"] = document_name
                        all_data.append(item)

                if extraction_result["skipped_pages"]:
                    skipped_pages.extend(extraction_result["skipped_pages"])

                # ✅ Per-document progress
                doc_progress = round((page_number / total_pages) * 100, 2)

                # ✅ Global progress update
                queue.put({
                    "document_name": document_name,
                    "page_number": page_number,
                    "total_pages": total_pages,
                    "progress": doc_progress,
                    "total_pages_global": total_pages_global,
                    "current_page_processed": 1  # ✅ Used for dynamic total progress
                })

            total_time = round(time.time() - start_time, 2)
            total_rows_extracted = len(all_data)
            avg_time_per_field = round(total_time / total_rows_extracted, 2) if total_rows_extracted > 0 else 0

            # ✅ Send final extracted data
            queue.put({
                "completed": True,
                "document_name": document_name,
                "total_time": total_time,
                "total_rows_extracted": total_rows_extracted,
                "avg_time_per_row": avg_time_per_field,
                "skipped_pages": skipped_pages,
                "extracted_data": all_data
            })

        except Exception as e:
            print(f"Error processing {document_name}: {str(e)}", flush=True)
            queue.put({"error": str(e)})


@app.route("/extract_text_stream", methods=["POST"])
def process_pdfs_stream():
    if "pdf" not in request.files or "prompt" not in request.form or "username" not in request.form or "password" not in request.form:
        return jsonify({"error": "Missing required parameters"}), 400

    username = request.form["username"]
    password = request.form["password"]

    if not authenticate_user(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    pdf_files = request.files.getlist("pdf")
    prompt = request.form["prompt"]

    temp_dir = tempfile.mkdtemp()
    pdf_paths = []
    total_pages_global = 0  # ✅ Track total pages globally

    for pdf_file in pdf_files:
        original_filename = pdf_file.filename
        safe_filename = "".join(c for c in original_filename if c.isalnum() or c in (" ", ".", "_")).strip()
        pdf_path = os.path.join(temp_dir, safe_filename)
        pdf_file.save(pdf_path)
        pdf_paths.append(pdf_path)

        # ✅ Count total pages per PDF before processing
        images = convert_from_path(pdf_path, fmt="jpeg")
        total_pages_global += len(images)

    print(f"Total pages across all PDFs: {total_pages_global}")

    queue = multiprocessing.Queue()
    processes = []
    processed_pages = 0  # ✅ Track pages processed globally

    for pdf_path in pdf_paths:
        process = multiprocessing.Process(target=process_pdf, args=(pdf_path, prompt, username, queue, total_pages_global))
        processes.append(process)
        process.start()

    def generate():
        nonlocal processed_pages
        all_extracted_data = []
        total_time = 0
        total_rows_extracted = 0
        skipped_pages = []
        active_processes = len(pdf_paths)
        document_progress = {}

        while active_processes > 0:
            data = queue.get()

            if "document_name" in data and "progress" in data:
                doc_name = data["document_name"]
                doc_progress = data["progress"]
                document_progress[doc_name] = doc_progress  

                # ✅ Yield per-document progress
                yield f"data: {json.dumps({'document_name': doc_name, 'progress': doc_progress})}\n\n"

            if "current_page_processed" in data:
                processed_pages += 1  
                total_progress = round((processed_pages / total_pages_global) * 100, 2)

                # ✅ Yield total progress dynamically
                yield f"data: {json.dumps({'total_progress': total_progress})}\n\n"

            if "extracted_data" in data and isinstance(data["extracted_data"], list):
                all_extracted_data.extend(data["extracted_data"])
            if "skipped_pages" in data and isinstance(data["skipped_pages"], list):
                skipped_pages.extend(data["skipped_pages"])

            if "total_time" in data:
                total_time += data["total_time"]
            if "total_rows_extracted" in data:
                total_rows_extracted += data["total_rows_extracted"]

            if "completed" in data:
                active_processes -= 1  

        for process in processes:
            process.join()

        # ✅ Save final extracted data
        if all_extracted_data:
            total_time = round(total_time, 2)
            avg_time_per_row = round(total_time / total_rows_extracted, 2) if total_rows_extracted > 0 else 0
            timestamp = int(time.time())
            combined_filename = f"output_data_{timestamp}.xlsx"
            combined_path = save_extracted_data_to_excel(all_extracted_data, combined_filename)

            # ✅ Final yield with completion status & download link
            yield f"data: {json.dumps({'completed': True, 'download_link': f'/download_excel?filename={combined_filename}', 'total_time': total_time, 'total_rows_extracted': total_rows_extracted, 'avg_time_per_row': avg_time_per_row})}\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream")



@app.route("/user_list", methods=["GET"])
def get_user_list():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT username FROM extraction_history")
    users = [row["username"] for row in cursor.fetchall()]

    conn.close()
    return jsonify({"users": users})


@app.route("/history", methods=["POST"])
def show_extraction_history():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    target_username = data.get("target_username", "").strip()  # ✅ Ensure target_username is properly formatted

    # ✅ Check authentication
    if not authenticate_user(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    conn = get_db()
    cursor = conn.cursor()

    # ✅ If the user is NOT an admin, show ONLY their history
    if username != "admin":
        target_username = username  # ✅ Force non-admins to see only their own history

    # ✅ Admin can filter by a specific user OR see all users
    if username == "admin":
        if target_username and target_username != "All Users":
            print(f"Admin fetching history for user: {target_username}")  # ✅ Debugging Log
            cursor.execute("SELECT * FROM extraction_history WHERE username = ? ORDER BY timestamp DESC", (target_username,))
        else:
            print("Admin fetching history for all users")  # ✅ Debugging Log
            cursor.execute("SELECT * FROM extraction_history ORDER BY timestamp DESC")
    else:
        print(f"User fetching history for self: {username}")  # ✅ Debugging Log
        cursor.execute("SELECT * FROM extraction_history WHERE username = ? ORDER BY timestamp DESC", (username,))

    history = cursor.fetchall()
    conn.close()

    return jsonify({
        "history": [
            {
                "username": row["username"],  # ✅ Include username
                "document_name": row["document_name"],
                "total_rows": row["total_rows"],
                "total_time": row["total_time"],
                "avg_time_per_field": round(float(row["total_time"]) / row["total_rows"], 2) if row["total_rows"] > 0 else 0,
                "timestamp": row["timestamp"]
            }
            for row in history
        ]
    })

@app.route("/stats", methods=["GET"])
def get_statistics():
    conn = get_db()
    cursor = conn.cursor()

    # Get total unique users who have processed at least one document
    cursor.execute("SELECT COUNT(DISTINCT username) FROM extraction_history")
    total_unique_users = cursor.fetchone()[0]

    # Get total documents processed
    cursor.execute("SELECT COUNT(DISTINCT document_name) FROM extraction_history")
    total_documents = cursor.fetchone()[0]

    # Get total rows processed
    cursor.execute("SELECT SUM(total_rows) FROM extraction_history")
    total_rows = cursor.fetchone()[0] or 0  # Handle NULL case

    conn.close()

    return jsonify({
        "total_users": total_unique_users,
        "total_documents_processed": total_documents,
        "total_rows_processed": total_rows
    })



@app.route("/user_stats", methods=["POST"])
def get_user_statistics():
    data = request.get_json()
    admin_username = data.get("admin_username")
    admin_password = data.get("admin_password")

    # Admin authentication
    if admin_username != "admin" or not authenticate_user(admin_username, admin_password):
        return jsonify({"error": "Only admin can access user statistics"}), 403

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            username, 
            COUNT(DISTINCT document_name) AS total_documents, 
            SUM(total_rows) AS total_rows, 
            SUM(total_time) AS total_time
        FROM extraction_history
        GROUP BY username
    """)
    
    user_stats = cursor.fetchall()
    conn.close()

    return jsonify({
        "user_statistics": [
            {
                "username": row["username"],
                "total_documents": row["total_documents"],
                "total_rows": row["total_rows"],
                "avg_time_per_row": round(row["total_time"] / row["total_rows"], 2) if row["total_rows"] > 0 else 0
            }
            for row in user_stats
        ]
    })


@app.route("/user_stats_self", methods=["POST"])
def get_user_statistics_self():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    # Authenticate user
    if not authenticate_user(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            COUNT(DISTINCT document_name) AS total_documents, 
            SUM(total_rows) AS total_rows, 
            SUM(total_time) AS total_time
        FROM extraction_history
        WHERE username = ?
    """, (username,))
    
    user_stat = cursor.fetchone()
    conn.close()

    # Handle empty stats case
    total_documents = user_stat["total_documents"] if user_stat["total_documents"] else 0
    total_rows = user_stat["total_rows"] if user_stat["total_rows"] else 0
    total_time = user_stat["total_time"] if user_stat["total_time"] else 0

    avg_time_per_row = round(total_time / total_rows, 2) if total_rows > 0 else 0

    return jsonify({
        
            "username": username,
            "total_documents": total_documents,
            "total_rows": total_rows,
            "avg_time_per_row": avg_time_per_row})


@app.route("/remove_user", methods=["POST"])
def remove_user():
    data = request.get_json()
    admin_username = data.get("admin_username")
    admin_password = data.get("admin_password")
    target_username = data.get("target_username")

    # Authenticate as admin
    if admin_username != "admin" or not authenticate_user(admin_username, admin_password):
        return jsonify({"error": "Only admin can remove users"}), 403

    # Prevent deletion of the admin account
    if target_username == "admin":
        return jsonify({"error": "Admin account cannot be deleted"}), 403

    conn = get_db()
    cursor = conn.cursor()

    # Check if the user exists before attempting deletion
    cursor.execute("SELECT * FROM users WHERE username = ?", (target_username,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"error": "User not found"}), 404

    # Delete the user
    cursor.execute("DELETE FROM users WHERE username = ?", (target_username,))
    conn.commit()
    conn.close()

    return jsonify({"message": f"User '{target_username}' removed successfully"}), 200


@app.route("/remove_all_users", methods=["POST"])
def remove_all_users():
    """Removes all users (except admin) and clears history."""
    data = request.get_json()
    admin_username = data.get("admin_username")
    admin_password = data.get("admin_password")

    # ✅ Authenticate as admin
    if admin_username != "admin" or not authenticate_user(admin_username, admin_password):
        return jsonify({"error": "Only admin can remove all users"}), 403

    conn = get_db()
    cursor = conn.cursor()

    try:
        # ✅ Move all non-admin users to `removed_users`
        cursor.execute("""
            INSERT INTO removed_users (username, removed_at)
            SELECT username, CURRENT_TIMESTAMP FROM users WHERE username != 'admin'
        """)

        # ✅ Delete all non-admin users
        cursor.execute("DELETE FROM users WHERE username != 'admin'")

        # ✅ Clear extraction history
        cursor.execute("DELETE FROM extraction_history")

        conn.commit()
        return jsonify({"message": "All users and history removed successfully, except admin"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to remove users: {str(e)}"}), 500

    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

    

