from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

UPLOAD_FOLDER = "uploads"
MERGED_FILE = "merged.json"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route("/merge", methods=["POST"])
def merge_json():
    files = request.files.getlist("jsonFiles")
    merged_data = {}

    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    for file in files:
        data = json.load(file)
        merged_data.update(data)  # Merging JSON objects

    with open(MERGED_FILE, "w") as f:
        json.dump(merged_data, f, indent=4)

    return send_file(MERGED_FILE, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
