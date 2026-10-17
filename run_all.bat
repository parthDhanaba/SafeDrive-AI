@echo off
title SafeDrive AI - Full System Launcher
echo ========================================================
echo        SafeDrive AI - Full System Launcher
echo ========================================================
echo 1. Launching Backend on http://127.0.0.1:5000 ...
start "SafeDrive AI - Backend" cmd /k "py server.py"
timeout /t 3 /nobreak >nul
echo 2. Launching Frontend on http://localhost:5173 ...
start "SafeDrive AI - Frontend" cmd /k "cd frontend && npm run dev"
echo ========================================================
echo System active. Dashboard URL: http://localhost:5173/
echo ========================================================
