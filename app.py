from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, Response, stream_with_context
import yt_dlp
import os
import requests
import zipfile
import shutil
import tempfile
from urllib.parse import urlparse
import re

app = Flask(__name__)

# --- Configuration ---
DOWNLOAD_FOLDER = "/tmp/mydownloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# --- Helper Functions (No changes required) ---
def categorize_formats(formats):
    categorized = {}
    
    # Sort formats by resolution (height) in descending order to find the best ones first
    formats.sort(key=lambda f: f.get('height') or 0, reverse=True)
    
    for f in formats:
        height = f.get('height')
        # We only care about video streams with a resolution (height)
        if f.get('vcodec') != 'none' and height:
            if height >= 2160 and '4K' not in categorized: categorized['4K'] = f
            elif height >= 1440 and '2K' not in categorized: categorized['2K'] = f
            elif height >= 1080 and '1080p' not in categorized: categorized['1080p'] = f
            elif height >= 720 and '720p' not in categorized: categorized['720p'] = f
            elif height >= 480 and '480p' not in categorized: categorized['480p'] = f
            elif height >= 360 and '360p' not in categorized: categorized['360p'] = f

    # Find the best muxed (video+audio) format for "Best Quality" option
    best_muxed = next((f for f in formats if f.get('vcodec') != 'none' and f.get('acodec') != 'none'), None)
    if best_muxed:
        categorized['Best Quality'] = best_muxed
    
    # Find the best audio-only format for the audio download option
    best_audio = next((f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none'), None)
    if best_audio:
        categorized['Best Quality (Audio)'] = best_audio
        
    return { 
        q: {
            'format_id': f['format_id'], 
            'ext': f.get('ext'), 
            'filesize': f.get('filesize'),
            'resolution': f.get('height')
        } 
        for q, f in categorized.items()
    }


def download_image(url, folder):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        filename = os.path.basename(urlparse(url).path) or "downloaded_image.jpg"
        filepath = os.path.join(folder, filename)
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return filename
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return None

# --- Main Routes ---
@app.route('/')
def downloader_page(): return render_template('index.html')
@app.route('/about')
def about(): return render_template('about.html')
@app.route('/blog')
def blog(): return render_template('blog.html')
@app.route('/themes')
def themes(): return render_template('themes.html')
@app.route('/docs')
def docs(): return render_template('docs.html')
@app.route('/services')
def services(): return render_template('services.html')
@app.route('/mydownloads/<filename>')
def downloaded_file(filename): return send_from_directory(app.config['DOWNLOAD_FOLDER'], os.path.basename(filename), as_attachment=True)

@app.route('/download_playlist')
def download_playlist():
    url = request.args.get('url'); temp_dir = tempfile.mkdtemp()
    try:
        ydl_opts = {'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'outtmpl': os.path.join(temp_dir, '%(playlist_index)s - %(title)s.%(ext)s'), 'noplaylist': False}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl: info = ydl.extract_info(url, download=True)
        playlist_title = info.get('title', 'playlist').strip().replace(' ', '_'); zip_filename = f"{playlist_title}.zip"; zip_filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], zip_filename)
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files: zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), temp_dir))
        return redirect(url_for('downloaded_file', filename=zip_filename))
    finally:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)

# --- API Routes ---
@app.route('/get_media_info', methods=['POST'])
def get_media_info():
    data = request.get_json()
    url = data.get('url')
    if not url: return jsonify({'error': 'URL is required'}), 400
    try:
        with yt_dlp.YoutubeDL({'noplaylist': True, 'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info.get('title') and info.get('is_live'):
                return jsonify({'error': 'Cannot download livestreams. The URL is for a live event.'}), 400
            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'formats': categorize_formats(info.get('formats', []))
            })
    except Exception as e:
        return jsonify({'error': "Could not retrieve video information. Please check the URL or try a different one."}), 500

@app.route('/download_media', methods=['POST'])
def download_media():
    data = request.get_json()
    url = data.get('url')
    media_type = data.get('type')
    format_id = data.get('format_id')
    
    if not url or not media_type:
        return "Error: URL and media type are required.", 400
    try:
        if media_type == 'image':
            filename = download_image(url, app.config['DOWNLOAD_FOLDER'])
            if not filename: return "Error: Could not download image.", 500
            return jsonify({'download_url': url_for('downloaded_file', filename=filename)})
        elif media_type == 'playlist':
            return redirect(url_for('download_playlist', url=url))
        elif media_type in ['video', 'audio']:
            # Correctly handle video download by merging best video and best audio
            if media_type == 'video':
                ydl_format_string = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            else:
                ydl_format_string = format_id if format_id else 'bestaudio/best'

            ydl_opts = {
                'format': ydl_format_string,
                'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s'),
                'noplaylist': True,
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}] if media_type == 'audio' else []
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            return jsonify({'download_url': url_for('downloaded_file', filename=os.path.basename(filename))})
        else:
            return "Error: Invalid media type specified.", 400
    except Exception as e:
        print(f"Error during download: {e}")
        return "An error occurred during download. The URL may be invalid, private, or not supported.", 500

