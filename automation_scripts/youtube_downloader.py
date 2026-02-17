import os
import yt_dlp

# Use the script's directory
download_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(download_dir, exist_ok=True)

def download_youtube_video(url, save_path=download_dir):
    ydl_opts = {
        'outtmpl': f'{save_path}/%(title)s.%(ext)s',
        'format': 'bestvideo+bestaudio/best',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

download_youtube_video("https://www.youtube.com/watch?v=jTW3Yi8o1XU")