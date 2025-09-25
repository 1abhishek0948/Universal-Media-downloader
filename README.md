# 🎬 Universal Media Downloader (UMD)

Universal Media Downloader (UMD) is a Flask-based web app that lets you download videos, playlists, and other media from multiple platforms using **yt-dlp**.  
It comes with a clean Bootstrap-powered UI, voice alert system (optional), and playlist support.

---

## ✨ Features
- 📥 Download videos from YouTube and other supported sites  
- 📂 Playlist downloads supported  
- 🎨 Clean UI with Bootstrap  
- ⚡ Fast backend powered by Flask + Gunicorn  
- 📑 Auto-generated `requirements.txt` for easy setup  

---

## 🛠️ Tech Stack
- **Backend:** Flask, Gunicorn, yt-dlp  
- **Frontend:** HTML, CSS, Bootstrap, JavaScript  
- **Deployment:** Gunicorn + Nginx (production ready)  

---

## 📦 Installation

### 1. Clone the repo
```bash
git clone https://github.com/YOUR-USERNAME/universal-downloader.git
cd universal-downloader
```

### 2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## 🚀 Run the App

### Development (Flask built-in server)
```bash
python app.py
```
Runs on [http://127.0.0.1:4000](http://127.0.0.1:4000)

### Production (Gunicorn)
```bash
gunicorn -w 4 -b 0.0.0.0:4000 app:app
```

---

## 📂 Project Structure
```
universal-downloader/
│── mydownloads/        # Downloaded media
│── static/             # Static files (CSS, JS, images)
│── templates/          # HTML templates
│── venv/               # Virtual environment (ignored in .gitignore)
│── app.py              # Flask entry point
│── requirements.txt    # Python dependencies
│── .gitignore          # Git ignore file
```

---

## 🌍 Deployment
1. Use **Gunicorn** as the WSGI server.  
2. Configure **Nginx** as a reverse proxy.  
3. (Optional) Add HTTPS with **Certbot**.  

---

## 📜 License

---

👨‍💻 Developed by [Abhishek Thakur](https://github.com/YOUR-USERNAME)
