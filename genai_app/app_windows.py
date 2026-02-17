from flask import Flask, request, jsonify, send_file, stream_with_context, Response, session
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

DB_FILE = "users.db"
load_dotenv()

# Google Cloud project details
project = os.getenv("GENAI_PROJECT")
location = os.getenv("GENAI_LOCATION")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
app.config['SECRET_KEY'] = 'key'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
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
        conn.commit()

        # Insert default admin user
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", "admin123"))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Admin already exists

init_db()


def hash_password(password):
    # Create a salt and hash the password
    salt = bcrypt.gensalt()  # Generates a new salt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password


def authenticate_user(username, password):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            print("User not found.")  # Debugging
            return False  # User does not exist

        stored_hashed_password = user[0]  # Stored hashed password from DB
        print(f"Stored hashed password: {stored_hashed_password}")  # Debugging

        # Ensure stored password is in bytes before using bcrypt.checkpw()
        if isinstance(stored_hashed_password, str):
            stored_hashed_password = stored_hashed_password.encode('utf-8')

        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):
            return True  # Password matches
        else:
            print("Password doesn't match.")  # Debugging

        return False
    except Exception as e:
        print(f"Error during authentication: {e}")
        return False  # Return False if an error occurs



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

# ✅ Background PDF Processing with Multiprocessing
def process_pdf(pdf_path, prompt, username, queue):
    document_name = os.path.basename(pdf_path)
    print("The doc name", document_name)
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            images = convert_from_path(pdf_path, output_folder=temp_dir, fmt="jpeg")
            total_pages = len(images)
            all_data = []
            skipped_pages = []
            start_time = time.time()
            # document_name = os.path.basename(pdf_path)

            for idx, image in enumerate(images):
                page_number = idx + 1
                image_path = os.path.join(temp_dir, f"page_{page_number}.jpg")
                image.save(image_path, "JPEG")

                # ✅ Extract text and include page number & document name
                extraction_result = extract_text_from_image(image_path, prompt, page_number)

                if extraction_result["extracted_data"]:
                    for item in extraction_result["extracted_data"]:
                        item["page_number"] = page_number
                        item["document_name"] = document_name
                        all_data.append(item)

                if extraction_result["skipped_pages"]:
                    skipped_pages.extend(extraction_result["skipped_pages"])

                # ✅ Send streaming update
                queue.put({"page_number": page_number, "total_pages": total_pages, "document_name": document_name})

            total_time = round(time.time() - start_time, 2)
            total_rows_extracted = len(all_data)
            avg_time_per_field = round(total_time / total_rows_extracted, 2) if total_rows_extracted > 0 else 0

            excel_filename = f"extracted_data_{int(time.time())}.xlsx"
            excel_path = save_extracted_data_to_excel(all_data, excel_filename)

            # ✅ Save extraction history in SQLite
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO extraction_history (username, document_name, total_rows, total_time)
                VALUES (?, ?, ?, ?)
            """, (username, document_name, total_rows_extracted, total_time))
            conn.commit()
            conn.close()

            # ✅ Send final processing results
            queue.put({
                "completed": True,
                "total_time": total_time,
                "total_rows_extracted": total_rows_extracted,
                "avg_time_per_row": avg_time_per_field,
                "skipped_pages": skipped_pages,
                "download_link": f"/download_excel?filename={excel_filename}"
            })

        except Exception as e:
            queue.put({"error": str(e)})

def save_extracted_data_to_excel(extracted_data, filename):
    df = pd.DataFrame(extracted_data)
    excel_path = os.path.join(tempfile.gettempdir(), filename)
    df.to_excel(excel_path, index=False)
    print(f"Excel file saved at: {excel_path}")
    return excel_path

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()  # Get JSON data from the request

    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Missing required parameters"}), 400

    username = data["username"]
    password = data["password"]

    if not authenticate_user(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Set user session
    session['username'] = username

    return jsonify({
        "message": "Login successful!",
        "username": username,
        "password": password
    })



@app.route('/change_password', methods=['POST'])
def change_password():
    if 'username' not in session:
        return jsonify({"error": "You must be logged in to change your password"}), 403

    if "current_password" not in request.form or "new_password" not in request.form:
        return jsonify({"error": "Missing required parameters"}), 400

    current_password = request.form["current_password"]
    new_password = request.form["new_password"]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (session["username"],))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "User not found"}), 404

    stored_hashed_password = user[0]
    print(f"Stored hashed password (from DB): {stored_hashed_password}")  # Debugging

    # Ensure it's bytes before checking with bcrypt
    if isinstance(stored_hashed_password, str):
        stored_hashed_password = stored_hashed_password.encode('utf-8')

    if not bcrypt.checkpw(current_password.encode(), stored_hashed_password):
        print("Current password does not match stored hash.")  # Debugging
        return jsonify({"error": "Current password is incorrect"}), 401

    # Hash the new password and update it
    hashed_new_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_new_password, session["username"]))
    conn.commit()
    conn.close()

    return jsonify({"message": "Password changed successfully!"})


# Logout endpoint to clear the session
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)  # Remove 'username' from session
    return jsonify({"message": "Logged out successfully!"})

@app.route("/create_user", methods=["POST"])
def create_user():
    data = request.get_json()

    admin_username = data.get("admin_username")
    admin_password = data.get("admin_password")
    new_username = data.get("new_username")
    new_password = data.get("new_password")

    # Admin authentication
    if admin_username != "admin" or not authenticate_user(admin_username, admin_password):
        return jsonify({"error": "Only admin can create users"}), 403

    # Validate inputs
    if not new_username or not new_password:
        return jsonify({"error": "New username and password required"}), 400

    try:
        # Hash the new password before storing
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_username, hashed_password))
        conn.commit()
        conn.close()

        return jsonify({"message": "User created successfully"}), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400
    

@app.route("/download_excel", methods=["GET"])
def download_excel():
    filename = request.args.get("filename")
    file_path = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404



# ✅ Streaming API for PDF Processing with Parallel Execution
@app.route("/extract_text_stream", methods=["POST"])
def process_pdf_stream():
    if "pdf" not in request.files or "prompt" not in request.form or "username" not in request.form or "password" not in request.form:
        return jsonify({"error": "Missing required parameters"}), 400

    username = request.form["username"]
    password = request.form["password"]

    if not authenticate_user(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    pdf_file = request.files["pdf"]
    prompt = request.form["prompt"]

    # ✅ Get the actual document name from the uploaded file
    original_filename = pdf_file.filename  # Gets the original filename
    print("Actual Document Name:", original_filename)  # Debugging

    # ✅ Clean the filename to remove special characters
    safe_filename = "".join(c for c in original_filename if c.isalnum() or c in (" ", ".", "_")).strip()

    # ✅ Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    # ✅ Save the PDF file with its original name in the temp directory
    pdf_path = os.path.join(temp_dir, safe_filename)
    pdf_file.save(pdf_path)

    print(f"PDF saved at: {pdf_path}")  # Debugging

    # ✅ Create a queue for inter-process communication
    queue = multiprocessing.Queue()

    # ✅ Start PDF extraction in a separate process (Non-blocking)
    process = multiprocessing.Process(target=process_pdf, args=(pdf_path, prompt, username, queue))
    process.start()

    def generate():
        while True:
            data = queue.get()  # ✅ Get progress updates from queue
            yield f"data: {json.dumps(data)}\n\n"

            if "completed" in data or "error" in data:
                break  # ✅ Stop streaming after completion

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
