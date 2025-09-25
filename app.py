from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
import yt_dlp
import os
import requests
import zipfile
import shutil
import tempfile
from urllib.parse import urlparse

app = Flask(__name__)

# --- Configuration ---
DOWNLOAD_FOLDER = 'mydownloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

# --- Helper Functions ---

def categorize_formats(formats):
    """Categorizes video formats into specific quality buckets."""
    categorized = {}
    for f in formats:
        if f.get('vcodec') == 'none' or f.get('acodec') == 'none':
            continue
        height = f.get('height')
        if not height:
            continue
        if height >= 2160 and '4K' not in categorized:
            categorized['4K'] = f
        elif height >= 1440 and '2K' not in categorized:
            categorized['2K'] = f
        elif height >= 1080 and '1080p' not in categorized:
            categorized['1080p'] = f
        elif height >= 720 and '720p' not in categorized:
            categorized['720p'] = f
        elif height >= 480 and 'Medium' not in categorized:
            categorized['Medium'] = f
        elif 'Low' not in categorized:
            categorized['Low'] = f

    simplified = {
        quality: {
            'format_id': f['format_id'],
            'ext': f['ext'],
            'height': f.get('height'),
            'filesize': f.get('filesize')
        }
        for quality, f in categorized.items()
    }
    return simplified

def download_image(url, folder):
    """Downloads a direct image from a URL."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path) or "downloaded_image.jpg"
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
def downloader_page():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/playlist')
def playlist():
    return render_template('playlist.html')

@app.route('/mydownloads/<filename>')
def downloaded_file(filename):
    safe_name = os.path.basename(filename)
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], safe_name, as_attachment=True)

# --- API Routes ---

@app.route('/get_media_info', methods=['POST'])
def get_media_info():
    data = request.get_json()
    url = data.get('url')
    media_type = data.get('type')

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    ydl_opts = {'noplaylist': True, 'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # This route is now only for single video/audio info
            if media_type == 'video':
                formats = info.get('formats', [])
                categorized_formats = categorize_formats(formats)
                return jsonify({
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'formats': categorized_formats,
                    'is_playlist': False
                })
            elif media_type == 'audio':
                return jsonify({
                    'title': info.get('title'),
                    'thumbnail': info.get('thumbnail'),
                    'is_playlist': False
                })
            else:
                return jsonify({'error': 'Invalid media type'}), 400

    except Exception as e:
        print(f"Error fetching media info: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_playlist')
def download_playlist():
    url = request.args.get('url')
    if not url:
        return "Error: URL is required for playlist download.", 400

    temp_dir = tempfile.mkdtemp()
    try:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'noplaylist': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            playlist_title = info.get('title', 'playlist')

        # Create a zip file of the downloaded videos
        zip_filename = f"{playlist_title}.zip"
        zip_filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], zip_filename)
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, temp_dir))
        
        return redirect(url_for('downloaded_file', filename=zip_filename))

    except Exception as e:
        print(f"Error during playlist download: {e}")
        return f"An error occurred during playlist download: {str(e)}", 500
    finally:
        # Clean up the temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@app.route('/download_media')
def download_media():
    url = request.args.get('url')
    media_type = request.args.get('type')
    format_id = request.args.get('format_id')

    if not url or not media_type:
        return "Error: URL and Type are required.", 400

    if media_type == 'playlist':
        return redirect(url_for('download_playlist', url=url))

    try:
        if media_type == 'image':
            filename = download_image(url, app.config['DOWNLOAD_FOLDER'])
            if not filename:
                return "Error: Could not download image.", 500
        else:
            ydl_opts = {}
            if media_type == 'audio':
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'noplaylist': True,
                }
            elif media_type == 'video':
                ydl_opts = {
                    'format': format_id or 'best',
                    'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s'),
                    'noplaylist': True,
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

                if media_type == 'audio':
                    base, _ = os.path.splitext(filename)
                    filename = base + '.mp3'

                filename = os.path.basename(filename)

        return redirect(url_for('downloaded_file', filename=filename))

    except Exception as e:
        print(f"Error during download: {e}")
        return f"An error occurred during download: {str(e)}", 500
