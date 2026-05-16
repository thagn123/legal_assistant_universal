@echo off
setlocal enabledelayedexpansion
title LexAI — Legal Intelligence Backend

echo ============================================================
echo  LexAI - Universal Legal Knowledge Assistant
echo ============================================================
echo.

:: ── Check Docker Desktop is running ─────────────────────────────────────────
docker --context desktop-linux info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running.
    echo         Please start Docker Desktop from the Start Menu,
    echo         wait for the whale icon to appear in the system tray,
    echo         then run this script again.
    pause
    exit /b 1
)
echo [OK] Docker Desktop is running.

:: ── Start MongoDB ────────────────────────────────────────────────────────────
echo [..] Starting MongoDB...
docker --context desktop-linux compose up -d mongodb
if errorlevel 1 (
    echo [ERROR] Failed to start MongoDB container.
    pause
    exit /b 1
)

:: ── Wait for MongoDB to be healthy ───────────────────────────────────────────
echo [..] Waiting for MongoDB to be ready (up to 60s)...
set /a tries=0
:waitloop
set /a tries+=1
docker --context desktop-linux inspect --format="{{.State.Health.Status}}" lka_mongodb 2>nul | findstr /i "healthy" >nul
if not errorlevel 1 goto mongo_ready
if !tries! GEQ 12 (
    echo [WARN] MongoDB health check timed out — continuing anyway.
    goto mongo_ready
)
timeout /t 5 /nobreak >nul
goto waitloop

:mongo_ready
echo [OK] MongoDB is ready.
echo.

:: ── Create data directories ──────────────────────────────────────────────────
if not exist "data\uploads" mkdir "data\uploads"
if not exist "data\reports" mkdir "data\reports"

:: ── Start API ────────────────────────────────────────────────────────────────
echo [..] Starting API server on http://localhost:8000
echo      Docs: http://localhost:8000/docs
echo      Health: http://localhost:8000/health
echo.
echo      Press Ctrl+C to stop.
echo.

set PYTHONUTF8=1
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

endlocal
