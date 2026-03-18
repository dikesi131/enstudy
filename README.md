# EnStudy

A full-stack English study system built with Python, React/Vite, and MySQL.

## Features

1. Show words and sample sentences by yearly/monthly/weekly review windows.
2. Play word audio from Youdao API and sentence audio via Piper TTS.
3. Import and export words/sentences.
4. View statistics about words and sentences.

## Stack

- Backend: FastAPI + SQLAlchemy
- Frontend: React + Vite
- Database: MySQL 8

## Local Development

Before running services, make sure local MySQL is available and `enstudy` database exists.

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/Activate.ps1(windows) or source .venv/Scripts/activate(linux/macos)
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Quickly Start

```bash
# windows
run start.bat

# linux or macos
chmod +x start.sh
start.sh

```

## Import Format

### JSON

```json
{
  "items": [
    {
      "word": "example",
      "sentence": "This is an example sentence."
    }
  ]
}
```

### CSV

- CSV headers: `word,sentence`
