@echo off
setlocal
if defined CONDA_EXE if exist "%CONDA_EXE%" goto conda_ready
where conda.exe >nul 2>nul
if not errorlevel 1 (
    set "CONDA_EXE=conda.exe"
    goto conda_ready
)
for %%C in (
    "%USERPROFILE%\miniconda3\Scripts\conda.exe"
    "%USERPROFILE%\anaconda3\Scripts\conda.exe"
    "%USERPROFILE%\miniforge3\Scripts\conda.exe"
    "%ProgramData%\miniconda3\Scripts\conda.exe"
    "%ProgramData%\anaconda3\Scripts\conda.exe"
) do if exist "%%~C" set "CONDA_EXE=%%~C"
if not defined CONDA_EXE (
    echo [ERROR] Conda could not be found on PATH or in a common install location.
    echo Run this app from an activated environment with: python -m lsl_gui
    pause
    exit /b 1
)
:conda_ready
cd /d "%~dp0"
"%CONDA_EXE%" run --no-capture-output -n mne-lsl python -m lsl_gui
if errorlevel 1 pause
