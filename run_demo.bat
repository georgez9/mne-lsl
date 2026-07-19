@echo off
setlocal
cd /d "%~dp0"

start "LSL Test Streams" cmd /k call "%~dp0run_test_streams.bat"
timeout /t 2 /nobreak >nul
call "%~dp0run_lsl_gui.bat"
