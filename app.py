import os
from flask import Flask, request, render_template, send_from_directory, redirect, url_for, flash
from werkzeug.utils import secure_filename

# Import libraries used in our transformation functions
import librosa
import soundfile as sf
import numpy as np
from pydub import AudioSegment
from pydub.generators import WhiteNoise
from spleeter.separator import Separator

# -----------------------------
# Configuration and Setup
# -----------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"  # for flashing messages if needed

# Folders for file management (make sure these exist or create them at startup)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
STEMS_FOLDER = os.path.join(BASE_DIR, "stems")
TEMP_FOLDER = os.path.join(BASE_DIR, "temp")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")

# Create directories if they do not exist
for folder in [UPLOAD_FOLDER, STEMS_FOLDER, TEMP_FOLDER, OUTPUT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["STEMS_FOLDER"] = STEMS_FOLDER
app.config["TEMP_FOLDER"] = TEMP_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

# Only allow mp3 uploads
ALLOWED_EXTENSIONS = {"mp3"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# -----------------------------
# Helper Functions
# -----------------------------

def separate_stems(input_file, output_dir):
    """
    Uses Spleeter to separate a song into 2 stems (vocals and accompaniment).
    The output will be saved in output_dir/<song_basename>/.
    """
    separator = Separator("spleeter:2stems")  # using the 2-stem model
    separator.separate_to_file(input_file, output_dir)


def get_stem_paths(output_dir, filename_base):
    """
    Given the Spleeter output folder and the file’s basename, return the paths for vocals and accompaniment.
    """
    stem_folder = os.path.join(output_dir, filename_base)
    vocals_path = os.path.join(stem_folder, "vocals.wav")
    instrumental_path = os.path.join(stem_folder, "accompaniment.wav")
    return vocals_path, instrumental_path


# --- Transformation functions ---
def transform_lofi(input_path, output_path):
    """
    Simulate a lofi style by low-passing the audio and overlaying subtle white noise.
    """
    # Load the instrumental track
    audio = AudioSegment.from_file(input_path)
    # Apply a low-pass filter (cut off frequencies above 3000 Hz)
    lofi_audio = audio.low_pass_filter(3000)
    # Generate subtle white noise (at -30 dBFS)
    noise = WhiteNoise().to_audio_segment(duration=len(audio), volume=-30)
    # Overlay the noise onto the track
    lofi_audio = lofi_audio.overlay(noise)
    # Export as WAV (to be merged later)
    lofi_audio.export(output_path, format="wav")


def transform_jazz(input_path, output_path):
    """
    Simulate a jazz style by applying a slight pitch shift (up by 2 semitones).
    """
    # Load using librosa (preserves original sampling rate)
    y, sr = librosa.load(input_path, sr=None)
    # Apply pitch shift (+2 semitones)
    y_shifted = librosa.effects.pitch_shift(y, sr, n_steps=2)
    # Write out the transformed audio
    sf.write(output_path, y_shifted, sr)


def transform_dubstep(input_path, output_path):
    """
    Simulate a dubstep style by lowering the pitch (by 2 semitones) and speeding up the tempo.
    """
    y, sr = librosa.load(input_path, sr=None)
    # Lower pitch by 2 semitones
    y_shifted = librosa.effects.pitch_shift(y, sr, n_steps=-2)
    # Speed up the track slightly (rate=1.1)
    y_stretched = librosa.effects.time_stretch(y_shifted, rate=1.1)
    sf.write(output_path, y_stretched, sr)


def merge_audio(vocals_path, instrumental_path, output_path):
    """
    Merge the vocals and transformed instrumental using Pydub. Both tracks are trimmed to the same duration.
    The final mix is exported as an MP3.
    """
    vocals = AudioSegment.from_file(vocals_path)
    instrumental = AudioSegment.from_file(instrumental_path)
    # Trim both to the shortest duration
    min_duration = min(len(vocals), len(instrumental))
    vocals = vocals[:min_duration]
    instrumental = instrumental[:min_duration]
    # Overlay vocals on top of the instrumental
    final_mix = instrumental.overlay(vocals)
    final_mix.export(output_path, format="mp3")


# -----------------------------
# Flask Routes
# -----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Ensure a file was uploaded
        if "file" not in request.files:
            flash("No file part in the request.")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("No file selected.")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # Secure the filename and save it to the UPLOAD folder
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)

            # Get the chosen style from the form (lofi, jazz, or dubstep)
            style = request.form.get("style", "").lower()
            if style not in ["lofi", "jazz", "dubstep"]:
                flash("Invalid style selected.")
                return redirect(request.url)

            # Use the filename (without extension) for naming outputs
            file_base = os.path.splitext(filename)[0]

            # STEP 1: Separate stems using Spleeter.
            separate_stems(file_path, app.config["STEMS_FOLDER"])
            vocals_path, instrumental_path = get_stem_paths(app.config["STEMS_FOLDER"], file_base)

            # Check that Spleeter produced the expected files
            if not os.path.exists(vocals_path) or not os.path.exists(instrumental_path):
                flash("Stem separation failed.")
                return redirect(request.url)

            # STEP 2: Apply the selected transformation to the instrumental stem.
            transformed_instrumental_path = os.path.join(
                app.config["TEMP_FOLDER"], f"{file_base}_{style}_transformed.wav"
            )
            if style == "lofi":
                transform_lofi(instrumental_path, transformed_instrumental_path)
            elif style == "jazz":
                transform_jazz(instrumental_path, transformed_instrumental_path)
            elif style == "dubstep":
                transform_dubstep(instrumental_path, transformed_instrumental_path)

            # STEP 3: Merge the original vocals with the transformed instrumental.
            final_output_filename = f"{file_base}_{style}_remix.mp3"
            final_output_path = os.path.join(app.config["OUTPUT_FOLDER"], final_output_filename)
            merge_audio(vocals_path, transformed_instrumental_path, final_output_path)

            # Render the result page with a download link
            return render_template("result.html", remix_file=final_output_filename)

        else:
            flash("Allowed file type is mp3.")
            return redirect(request.url)

    return render_template("index.html")


@app.route("/download/<filename>")
def download_file(filename):
    """
    Route to download the final remixed file.
    """
    return send_from_directory(app.config["OUTPUT_FOLDER"], filename, as_attachment=True)


if __name__ == "__main__":
    # Run the Flask app in debug mode (disable debug in production)
    app.run(debug=True)
