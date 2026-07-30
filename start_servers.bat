@echo off
title Deep Research Agent — Starting Servers
echo Starting Backend (port 8000) and Frontend (port 3000)...

start "Backend" cmd /k "cd /d D:\deep_research_agent\backend && C:\Python314\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000"
ping -n 4 127.0.0.1 >nul
start "Frontend" cmd /k "cd /d D:\deep_research_agent\frontend && npm run dev"

echo.
echo Both servers started in separate windows.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo Close the windows to stop the servers.
pause
