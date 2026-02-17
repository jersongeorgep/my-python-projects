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
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "peppy-linker-332510-c7733d076051.json"
app.config['SECRET_KEY'] = 'Genaiapplication'

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

        if user:
            stored_hashed_password = user[0]
            print(f"Stored hashed password: {stored_hashed_password}")  # Debugging line

            # Check if the password matches the stored hash
            if bcrypt.checkpw(password.encode('utf-8'), stored_hashed_password):
                return True  # Password matches
            else:
                print("Password doesn't match.")  # Debugging line
        else:
            print("User not found.")  # Debugging line
            
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
    data = request.get_json()  # Get JSON data from the request body
    
    """ if 'username' not in session:
        return jsonify({"error": "You must be logged in to change your password"}), 403 """


    if not data or "current_password" not in data or "new_password" not in data:
        return jsonify({"error": "Missing required parameters"}), 400

    current_password = data["current_password"]
    new_password = data["new_password"]

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (data["username"],))
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
    cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_new_password, data["username"]))
    conn.commit()
    conn.close()

    return jsonify({"message": "Password changed successfully!"})

@app.route("/create_user", methods=["POST"])
def create_user():
    data = request.json
    admin_username, admin_password = data.get("admin_username"), data.get("admin_password")
    new_username, new_password = data.get("new_username"), data.get("new_password")
    
    if admin_username != "admin" or not authenticate_user(admin_username, admin_password):
        return jsonify({"error": "Only admin can create users"}), 403

    if not new_username or not new_password:
        return jsonify({"error": "New username and password required"}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_username, new_password))
        # hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        # cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_username, hashed_password))

        conn.commit()
        return jsonify({"message": "User created successfully"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400


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



# ✅ Background PDF Processing with Multiprocessing

def process_pdf(pdf_path, prompt, username, queue):
    document_name = os.path.basename(pdf_path)
    print("Processing document:", document_name)

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

                # ✅ Extract text and include page number & document name
                extraction_result = extract_text_from_image(image_path, prompt, page_number)

                if extraction_result["extracted_data"]:
                    for item in extraction_result["extracted_data"]:
                        item["page_number"] = page_number
                        item["document_name"] = document_name
                        all_data.append(item)

                if extraction_result["skipped_pages"]:
                    skipped_pages.extend(extraction_result["skipped_pages"])

                # ✅ Send *document-wise* progress update
                queue.put({
                    "document_name": document_name,
                    "page_number": page_number,
                    "total_pages": total_pages,
                    "progress": round((page_number / total_pages) * 100, 2)  # ✅ Update document progress
                })

            total_time = round(time.time() - start_time, 2)
            total_rows_extracted = len(all_data)
            avg_time_per_field = round(total_time / total_rows_extracted, 2) if total_rows_extracted > 0 else 0

            # ✅ Save extraction history in SQLite
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO extraction_history (username, document_name, total_rows, total_time)
                VALUES (?, ?, ?, ?)
            """, (username, document_name, total_rows_extracted, total_time))
            conn.commit()
            conn.close()

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
            queue.put({"error": str(e)})


# ✅ Streaming API for PDF Processing with Parallel Execution
@app.route("/extract_text_stream", methods=["POST"])
def process_pdfs_stream():
    if "pdf" not in request.files or "prompt" not in request.form or "username" not in request.form or "password" not in request.form:
        return jsonify({"error": "Missing required parameters"}), 400

    username = request.form["username"]
    password = request.form["password"]

    if not authenticate_user(username, password):
        return jsonify({"error": "Invalid credentials"}), 401

    pdf_files = request.files.getlist("pdf")  # ✅ Get multiple PDFs
    prompt = request.form["prompt"]

    temp_dir = tempfile.mkdtemp()
    pdf_paths = []
    for pdf_file in pdf_files:
        original_filename = pdf_file.filename
        safe_filename = "".join(c for c in original_filename if c.isalnum() or c in (" ", ".", "_")).strip()
        pdf_path = os.path.join(temp_dir, safe_filename)
        pdf_file.save(pdf_path)
        pdf_paths.append(pdf_path)

    print(f"PDFs saved at: {pdf_paths}")  # ✅ Debugging

    queue = multiprocessing.Queue()
    processes = []

    total_pdfs = len(pdf_paths)
    processed_pdfs = 0  # ✅ Declare it in outer scope

    for pdf_path in pdf_paths:
        process = multiprocessing.Process(target=process_pdf, args=(pdf_path, prompt, username, queue))
        processes.append(process)
        process.start()

    def generate():
        nonlocal processed_pdfs  
        all_extracted_data = []
        total_time = 0
        total_rows_extracted = 0
        skipped_pages = []
        active_processes = len(pdf_paths)
        document_progress = {}  # ✅ Track document-wise progress

        while active_processes > 0:
            data = queue.get()

            if "document_name" in data and "progress" in data:
                document_progress[data["document_name"]] = data["progress"]

                # ✅ Send real-time document progress update
                yield f"data: {json.dumps({'document_progress': document_progress})}\n\n"

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
                processed_pdfs += 1  
                total_progress = round((processed_pdfs / total_pdfs) * 100, 2)

                # ✅ Send total progress update
                yield f"data: {json.dumps({'total_progress': total_progress})}\n\n"

        for process in processes:
            process.join()

        # ✅ Save final extracted data
        if all_extracted_data:
            total_time = round(total_time, 2)
            avg_time_per_row = round(total_time / total_rows_extracted, 2) if total_rows_extracted > 0 else 0
            timestamp = int(time.time())
            combined_filename = f"output_data_{timestamp}.xlsx"
            combined_path = save_extracted_data_to_excel(all_extracted_data, combined_filename)

            # ✅ Send final response
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

    

