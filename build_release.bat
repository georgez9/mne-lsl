@echo off
setlocal
cd /d "%~dp0"
if defined CONDA_PREFIX if exist "%CONDA_PREFIX%\python.exe" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_release.ps1" -Python "%CONDA_PREFIX%\python.exe"
) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_release.ps1" -Python python
)
if errorlevel 1 pause
