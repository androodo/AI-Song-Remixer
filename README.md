# AI-Powered Song Remix Generator

An AI-powered web application that takes an MP3 song, separates it into vocal and instrumental stems, applies a style transfer effect (Lofi, Jazz, or Dubstep) to the instrumental, and then merges the vocals back in to produce a remixed version of the original song.

## Features

- **Stem Separation:** Uses [Spleeter](https://github.com/deezer/spleeter) to split any MP3 file into vocals and accompaniment.
- **Style Transfer:** Simulates different remix styles:
  - **Lofi Beat:** Applies a low-pass filter and overlays subtle white noise.
  - **Jazz Version:** Applies a slight pitch shift.
  - **Dubstep Drop:** Lowers the pitch and speeds up the tempo.
- **Modern Frontend:** Built with [Flask](https://flask.palletsprojects.com/) and [Bootstrap 5](https://getbootstrap.com/) for a responsive and modern user interface.
- **Easy to Use:** Upload your MP3, select your desired remix style, and download the remixed song.

## Tech Stack

- **Backend:** Python, Flask
- **Audio Processing:** Librosa, Pydub, Spleeter, TensorFlow
- **Frontend:** HTML, CSS, Bootstrap 5
- **Others:** NumPy, SoundFile

## Demo

![Demo Screenshot](path/to/screenshot.png)  
*frontend still in progress*

## Prerequisites

- **Python 3.8+**
- **ffmpeg:** Make sure [ffmpeg](https://ffmpeg.org/download.html) is installed and available in your system's PATH, as it is required by both Pydub and Spleeter.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/ai_song_remix_generator.git
   cd ai_song_remix_generator
