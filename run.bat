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
pip install -r requirements.txt

:: Check if FFmpeg is installed
where ffmpeg > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    :: Try to auto-detect a downloaded ffmpeg.exe and set FFMPEG_PATH for this session
    set "FFMPEG_PATH="

    :: Common location
    if exist "C:\ffmpeg\bin\ffmpeg.exe" set "FFMPEG_PATH=C:\ffmpeg\bin\ffmpeg.exe"

    :: Look for typical extract layout in Downloads: **\bin\ffmpeg.exe
    if "%FFMPEG_PATH%"=="" (
        for /r "%USERPROFILE%\Downloads" %%F in (ffmpeg.exe) do (
            echo %%~dpF | findstr /i "\\bin\\" > nul
            if not errorlevel 1 (
                set "FFMPEG_PATH=%%F"
                goto ffmpeg_found
            )
        )
    )

    :ffmpeg_found
    if not "%FFMPEG_PATH%"=="" (
        echo Found FFmpeg at: %FFMPEG_PATH%
    ) else (
        echo WARNING: FFmpeg is not found in your PATH and was not auto-detected.
        echo For full audio processing functionality, please install FFmpeg:
        echo 1. Download FFmpeg from https://github.com/BtbN/FFmpeg-Builds/releases
        echo 2. Extract the zip file
        echo 3. Add the bin folder to your PATH
        echo.
        echo The app will run in simulation mode if FFmpeg is not installed.
        echo.
        pause
    )
)

:: Start the application
echo Starting the application...
python app.py

pause