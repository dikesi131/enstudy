@echo off
setlocal

set "ROOT=%~dp0"

echo [EnStudy] Starting backend and frontend...

if exist "%ROOT%backend\.venv\Scripts\activate.bat" (
    start "EnStudy Backend" cmd /k "cd /d ""%ROOT%backend"" && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
) else (
    start "EnStudy Backend" cmd /k "cd /d ""%ROOT%backend"" && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
)
start "EnStudy Frontend" cmd /k "cd /d ""%ROOT%frontend"" && npm run dev"

echo [EnStudy] Backend:  http://127.0.0.1:8000
echo [EnStudy] Frontend: http://127.0.0.1:5173
echo [EnStudy] Two new terminal windows were opened for services.
