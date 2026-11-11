@echo off
title InsightForge AI Launcher
echo ==========================================================
echo Starting InsightForge AI - Research & Decision Intelligence
echo ==========================================================

echo Starting FastAPI Backend on port 8000...
start "InsightForge Backend" cmd /k ".\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak >nul

echo Starting Vite Frontend on port 5173...
start "InsightForge Frontend" cmd /k "cd frontend && npm run dev -- --host 127.0.0.1"

timeout /t 2 /nobreak >nul
echo ==========================================================
echo Opening browser at http://127.0.0.1:5173/ ...
start http://127.0.0.1:5173/
echo All services running! Keep the backend & frontend windows open.
echo ==========================================================

