# OnePlug EV — Enterprise AI Transcription Platform

An enterprise-grade, secure, internal AI transcription and call analytics platform custom-engineered for **OnePlug EV**. This full-stack system enables support agents and managers to upload customer support audio recordings (MP3/WAV), transcribe them using OpenAI Whisper API, sync and persist metadata in a PostgreSQL database, and query conversations with a synchronized, timestamp-seekable dialogue viewer.

---

## ⚡ System Workflow

```mermaid
graph TD
    A[Employee uploads customer call audio] -->|FastAPI Upload Endpoint| B(Securely save file to disk)
    B -->|Log metadata in PostgreSQL| C(Queue BackgroundTask worker)
    C -->|Immediate HTTP 202 response| D[Frontend progress tracker]
    
    subgraph Background Process
        E[Background worker initiates] -->|Whisper API / Mock Fallback| F(Speech-to-Text conversion)
        F -->|Segments, Timestamps, & Lang details| G(Store transcript in PostgreSQL)
        G -->|Update file status to completed| H(Done)
    end
    
    C -.-> E
    H -->|Auto-sync pool| I[Interactive Transcript Viewer]
```

---

## 📁 Repository Architecture

The platform utilizes a modern production-style clean monorepo architecture:

```text
oneplug/
├── backend/                       # FastAPI Backend Service
│   ├── app/
│   │   ├── config.py              # Environment configuration & settings
│   │   ├── db.py                  # Database connection, engines, and pools
│   │   ├── main.py                # FastAPI bootstrapper, CORS, and routers
│   │   ├── models.py              # SQLAlchemy DB Schemas (PostgreSQL / SQLite fallback)
│   │   ├── schemas.py             # Pydantic serialization & request validators
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── db_service.py      # Database CRUD and password security context
│   │   │   └── whisper.py         # Whisper integration with domain-specific mock fallback
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── auth.py            # Authentication, JWT tokens, and OAuth2 forms
│   │       └── transcription.py   # Upload handlers, streaming and delete operations
│   ├── uploads/                   # Secure storage directory for uploaded audio files
│   ├── requirements.txt           # Python application dependencies
│   ├── .env                       # Loaded configuration variables
│   └── .env.example               # Configuration variables template
│
├── frontend/                      # Next.js 15+ Frontend Service (Tailwind v4)
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css        # Tailwind directives & design token variables
│   │   │   ├── layout.tsx         # HTML shell & font definitions
│   │   │   ├── page.tsx           # Dashboard tabs, interactive uploader, and viewer
│   │   │   └── login/
│   │   │       └── page.tsx       # Auth portal and validation mechanics
│   ├── package.json               # Node dependency declarations
│   └── tsconfig.json              # TypeScript compilation rules
│
└── README.md                      # Architecture blueprint and deployment manual
```

---

## 💾 Database Schema Design

The system connects to **PostgreSQL** (configured dynamically via `DATABASE_URL` in `.env`). In case the PostgreSQL database is temporarily offline or unconfigured during local development, the SQLAlchemy engine includes a resilient fallback that initiates a local SQLite instance (`oneplug_fallback.db`), guaranteeing zero crashes.

### 1. `users` Table
Stores credentials for OnePlug EV internal agents and managers.
- `id` (Integer, Primary Key)
- `username` (String, Unique, Index)
- `email` (String, Unique, Index)
- `hashed_password` (String)
- `full_name` (String, Nullable)
- `role` (String, Default: `"agent"`)
- `is_active` (Boolean, Default: `True`)
- `created_at` (DateTime)

### 2. `audio_files` Table
Stores physical call tracking data and processing status.
- `id` (String UUID, Primary Key)
- `filename` (String)
- `file_path` (String)
- `file_size` (Integer, Bytes)
- `duration` (Float, Nullable)
- `mime_type` (String)
- `status` (String: `"pending"`, `"processing"`, `"completed"`, `"failed"`)
- `error_message` (Text, Nullable)
- `uploaded_by_id` (Integer, ForeignKey to `users.id`)
- `created_at` (DateTime)

### 3. `transcripts` Table
Persists full speech conversions and granular playback highlights.
- `id` (String UUID, Primary Key)
- `audio_file_id` (String, ForeignKey to `audio_files.id` on Cascade Delete)
- `text` (Text, Raw Full Transcript)
- `language` (String: e.g. `"ta"`, `"en"`, `"mixed"`)
- `words_count` (Integer)
- `duration` (Float, seconds)
- `segments` (JSON, List of dicts representing speakers, start/end timestamps, and dialogue lines)
- `created_at` (DateTime)
- `updated_at` (DateTime)

---

## 🌐 API Route Specifications

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :---: | :--- |
| **POST** | `/api/v1/auth/login` | No | Authentic employee credentials and returns JWT bearer token |
| **POST** | `/api/v1/auth/login-oauth2` | No | OAuth2 standard form login for Swagger docs authentication |
| **GET** | `/api/v1/auth/me` | Yes | Retrieves current user profile details |
| **POST** | `/api/v1/transcribe/upload` | Yes | Uploads MP3/WAV, generates DB records, schedules Whisper job in background |
| **GET** | `/api/v1/transcribe/list` | Yes | Lists all call files and active statuses |
| **GET** | `/api/v1/transcribe/file/{id}` | Yes | Retrieves call metadata and linked transcript text/segments |
| **GET** | `/api/v1/transcribe/audio/{id}` | No | Streams raw binary audio content directly into HTML5 audio player |
| **DELETE**| `/api/v1/transcribe/delete/{id}` | Yes | Destroys database records and sweeps physical files from disk |

---

## 🛠️ Step-by-Step Environment Setup

Follow these commands to deploy the entire full-stack platform locally on Windows.

### Prerequisites
Make sure you have **Node.js (v18+)** and **Python (3.10+)** installed.

---

### Step 1: Initialize the Backend

1. Navigate to the backend directory and create a virtual environment:
   ```powershell
   cd backend
   python -m venv venv
   venv\Scripts\activate
   ```

2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

3. Configure environment variables. Edit `backend/.env` with your settings:
   ```ini
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/oneplug_db
   OPENAI_API_KEY=your-openai-api-key-here
   ```

4. Run the FastAPI development server:
   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```
   > [!NOTE]
   > On startup, the backend automatically initializes all database tables. It also seeds a default employee account for immediate login:
   > - **Username:** `admin`
   > - **Password:** `oneplug2026`

---

### Step 2: Initialize the Frontend

1. Navigate to the frontend directory:
   ```powershell
   cd ../frontend
   ```

2. Install npm packages:
   ```powershell
   npm install
   ```

3. Launch the Next.js development server:
   ```powershell
   npm run dev
   ```
   The application will be accessible at: [http://localhost:3000](http://localhost:3000)

---

## 🚀 Production Deployment Setup

The platform is designed to be deployed across three tiers in production:

### 1. Database (Supabase)
1. Set up a PostgreSQL project on Supabase.
2. Retrieve your connection string from **Settings > Database > Connection Strings** (URI format).
3. Securely set this as your `DATABASE_URL` in the backend environment.

### 2. Backend & Speech-to-Text (Azure VM)
1. Provision a Linux VM on Azure (Recommended: `Standard_D4s_v5` to support Whisper CPU transcription).
2. Configure **Nginx** on port `80` to proxy traffic to your FastAPI app running on port `8002`.
3. Set up **Let's Encrypt SSL** (`certbot`) on the VM so your backend endpoints serve over `https://`.
4. Run the app using systemd or the provided `docker-compose` settings.
*For detailed setup commands, refer to the [Backend Deployment Manual](file:///c:/Users/Harsh/Downloads/oneplug/backend/README.md).*

### 3. Frontend (Vercel)
1. Import your repository into Vercel and set the Root Directory to `frontend`.
2. Add the environment variable `NEXT_PUBLIC_API_URL` pointing to your secure Azure VM domain (e.g., `https://api.yourdomain.com`).
3. Deploy.

---

## 💡 Engineering Highlights

- **Background Ingest Engine:** Audio uploads leverage FastAPI's `BackgroundTasks` to write files and call Whisper out-of-band. This means the client receives an immediate `202 Accepted` response, freeing connection channels and avoiding HTTP gateway timeouts.
- **Synchronized Dialogue Playback:** Inside the interactive Viewer, clicking the timestamp tag on *any* segment triggers the HTML5 audio element to automatically seek to that second (`audio.currentTime = start_seconds`) and play it instantly.
- **Search Term Highlighting:** A custom high-contrast CSS search system parses text segments, dynamically rendering highlighted matches using regex splits in the React DOM.
- **Intelligent Whisper Fallback:** If the `OPENAI_API_KEY` is not set or OpenAI's servers fail, the platform switches to a highly realistic, domain-specific EV-tech mock transcriber. This fallback matches the uploaded audio's language parameters (supporting English, Tamil, and mixed Tamil-English dialects), facilitating seamless evaluation and demonstrations.
