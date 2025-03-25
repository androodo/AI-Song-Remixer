@echo off
echo Starting AI Song Remixer...

:: Check if pip is installed
where pip > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: pip is not installed. Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Create folders if they don't exist
if not exist "app\static\uploads" mkdir "app\static\uploads"
if not exist "app\templates" mkdir "app\templates"

:: Install required packages if not already installed
echo Installing required packages...
pip install flask==2.0.1 Werkzeug==2.0.1 requests==2.27.1

:: Check if FFmpeg is installed
where ffmpeg > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: FFmpeg is not found in your PATH.
    echo For full audio processing functionality, please install FFmpeg:
    echo 1. Download FFmpeg from https://github.com/BtbN/FFmpeg-Builds/releases
    echo 2. Extract the zip file
    echo 3. Add the bin folder to your PATH
    echo.
    echo The app will run in simulation mode if FFmpeg is not installed.
    echo.
    pause
)

:: Start the application
echo Starting the application...
python app.py

pause