@echo off
setlocal
cd /d "%~dp0"
title Findora Portable
if not exist "runtime\python\python.exe" (
 echo Embedded Python runtime is missing. Run SETUP.bat first.
 pause
 exit /b 1
)
if not exist "data\findora.db" (
 "runtime\python\python.exe" app\server.py --init-only
)
if exist "models\qwen-7b-q5.gguf" if exist "runtime\llama\llama-server.exe" (
 start "Findora Local AI" /min cmd /c "runtime\llama\llama-server.exe -m models\qwen-7b-q5.gguf --host 127.0.0.1 --port 8081 --ctx-size 4096 --threads 6 --threads-batch 6 --no-webui > logs\llama.log 2>&1"
)
start "Findora" http://127.0.0.1:8765
"runtime\python\python.exe" app\server.py
