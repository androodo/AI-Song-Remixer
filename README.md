# AI Song Remixer

A web application that applies style effects to your uploaded music files using audio processing techniques.

## Features

- Upload MP3 or WAV audio files
- Choose from different style effects:
  - Lo-Fi: Creates authentic vintage sound with reduced sample rate, pitch shift, strong low-pass filtering, vinyl crackle, vibrato, tremolo, and heavy compression
  - Jazz: Transforms tracks with dramatically enhanced mid frequencies, multiple layers of reverb, sophisticated echo patterns, and rich harmonic enhancements
  - Dubstep: Applies extreme bass enhancement, aggressive wobble effects, dynamic compression for pumping, and volume boost for maximum impact
- Listen to your remixed song in the browser
- Download the processed song

## Requirements

- Python (any recent version)
- FFmpeg (for audio processing)
- Internet connection (for web-based resources)

## Quick Start (Windows)

1. Double-click the `run.bat` file
2. Wait for the application to start (a console window will open)
3. Open your web browser and go to `http://127.0.0.1:5000`
4. Upload a song and select your preferred style
5. Enjoy your remixed track!

## FFmpeg Installation

For full audio processing functionality, you'll need FFmpeg:

### Windows
1. Download from [FFmpeg Builds](https://github.com/BtbN/FFmpeg-Builds/releases)
2. Extract the zip file
3. Add the bin folder to your system PATH:
   - Right-click Computer/This PC → Properties → Advanced System Settings
   - Click Environment Variables
   - Edit the PATH variable to include the path to FFmpeg's bin folder

### Mac
```
brew install ffmpeg
```

### Linux
```
sudo apt update
sudo apt install ffmpeg
```

## Manual Setup

If you prefer to run the application manually:

1. Make sure Python is installed
2. Open a terminal or command prompt
3. Install the required packages:
   ```
   pip install flask==2.0.1 Werkzeug==2.0.1 requests==2.27.1 pydub==0.25.1
   ```
4. Run the application:
   ```
   python app.py
   ```
5. Open your web browser and go to `http://127.0.0.1:5000`

## How It Works

This application uses audio processing to add style effects to your music:

1. **Upload**: User uploads an MP3 or WAV file through the web interface
2. **Style Selection**: User chooses a style effect to apply
3. **Processing**: The app processes the audio using pydub to apply various effects:
   - For Lo-Fi: Reduces sample rate, applies low-pass filter, adds vinyl noise
   - For Jazz: Enhances mid frequencies, adds reverb, boosts bass
   - For Dubstep: Heavy bass enhancement, creates wobble effect
4. **Result**: User can listen to and download the result

## Troubleshooting

- **File Upload Issues**: Make sure your file is an MP3 or WAV and under 16MB
- **Application Won't Start**: Ensure Python is installed correctly
- **Audio Processing Fails**: Make sure FFmpeg is installed and in your PATH
- **Browser Can't Connect**: Check if the application is running and try the exact URL `http://127.0.0.1:5000`

## License

This project is open source and available under the MIT License. 