# OnePlug EV Speech Portal - Backend Production Deployment Guide

This backend is built with FastAPI, Whisper (STT), and SQLAlchemy. It connects to a Supabase managed PostgreSQL database.

## Production Deployment Checklist

### 1. Prerequisite Environment Variables
Before running the container in production, create a `.env` file containing:
```ini
APP_NAME="OnePlug EV AI Transcription Platform"
DEBUG=False
DATABASE_URL="postgresql://postgres.[YOUR_PROJECT_ID]:[YOUR_PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require&supa-pooler=transaction"
SECRET_KEY="[YOUR_GENERATED_RANDOM_LONG_SECRET_KEY]"
UPLOAD_DIR="/app/uploads"
GEMINI_API_KEY="[YOUR_GEMINI_API_KEY]"
```

---

### 2. Option A: Run via Docker (Recommended)

To build and run the backend using Docker Compose:
```bash
# Build the container
docker compose build

# Start the container in detached mode
docker compose up -d
```
The FastAPI backend will start listening on port `8002`.

---

### 3. Option B: Manual Host Setup (Nginx + systemd)

If running natively on the Azure VM host:
1. **Dependencies**: Ensure `ffmpeg` is installed:
   ```bash
   sudo apt update && sudo apt install -y ffmpeg
   ```
2. **Virtual Environment**: Create a venv and install requirements:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **systemd service**: Configure the service `/etc/systemd/system/oneplug-backend.service`:
   ```ini
   [Unit]
   Description=OnePlug EV Speech Portal Backend
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/var/www/oneplug/backend
   ExecStart=/var/www/oneplug/backend/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
4. **Start the Service**:
   ```bash
   sudo systemctl enable oneplug-backend
   sudo systemctl start oneplug-backend
   ```

---

### 4. Nginx Reverse Proxy & SSL (Let's Encrypt)
Configure Nginx (`/etc/nginx/sites-available/oneplug`):
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    client_max_body_size 50M; # allow larger audio uploads

    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
Link the site and obtain SSL using certbot:
```bash
sudo ln -s /etc/nginx/sites-available/oneplug /etc/nginx/sites-enabled/
sudo systemctl restart nginx
sudo certbot --nginx -d api.yourdomain.com
```
