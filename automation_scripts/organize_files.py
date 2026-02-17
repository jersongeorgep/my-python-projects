import os
import shutil

folder_path = "/home/allianze/Downloads"

file_types = {
    'Images': [".jpg", ".png", ".jpeg", ".webp", ".gif", ".svg", ".ico"],
    'Videos': [".mp4", ".avi", ".mkv", ".webm"],
    'Documents': [".doc", ".docx", ".txt", ".odt", ""],
    'PDFs': [".pdf"],
    'Spreadsheets': [".xlsx", ".xls", ".csv", ".ods"],
    'Archives': [".zip", ".tar.gz", ".rar", ".deb", ".exe", ".run"],
    'Audio': [".mp3", ".wav", ".ogg"],
    'DataBaseFiles' : [".db", ".sql"],
    'Json' : [".json"],
    "Pub" : [".pub"],
    "Html" : [".html", '.css', '.js', '.py', ".php", ".xml", ".jsx"],
}

for filename in os.listdir(folder_path):
    file_path = os.path.join(folder_path, filename)

    if os.path.isfile(file_path):
        file_extension = os.path.splitext(filename)[1].lower()  # use 'filename' not full 'file_path'

        for category, extensions in file_types.items():
            if file_extension in extensions:
                target_folder = os.path.join(folder_path, category)
                os.makedirs(target_folder, exist_ok=True)
                shutil.move(file_path, os.path.join(target_folder, filename))
                print(f"Moved '{filename}' to '{category}' folder.")
                break
