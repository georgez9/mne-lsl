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
    echo Activate the mne-lsl environment and run:
    echo python scripts\simulate_lsl_streams.py
    pause
    exit /b 1
)

:conda_ready
cd /d "%~dp0"
echo ============================================================
echo LSL test streams
echo   Demo-EEG:    4 EEG-like channels at 100 Hz
echo   Demo-Aux:    respiration and temperature at 40 Hz
echo   Demo-Events: event codes at 5 Hz
echo.
echo Keep this window open while testing the GUI.
echo Press Ctrl+C or close this window to stop the test streams.
echo ============================================================
echo.

"%CONDA_EXE%" run --no-capture-output -n mne-lsl python scripts\simulate_lsl_streams.py
if errorlevel 1 (
    echo.
    echo [ERROR] The test streams stopped unexpectedly.
    pause
)
