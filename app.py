import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import uuid
import shutil
import time
import requests
import json
import random
import subprocess
from datetime import datetime

# User's specific FFmpeg path
FFMPEG_PATH = r"C:\Users\doand\Downloads\ffmpeg-master-latest-win64-gpl-shared\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"

app = Flask(__name__, static_folder='app/static', template_folder='app/templates')
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOAD_FOLDER'] = os.path.join('app', 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg', 'm4a'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Get the current year for copyright in footer
    now = datetime.now()
    return render_template('index.html', now=now)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'warning')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'warning')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Save the uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Get selected effect
        effect = request.form.get('effect', 'lofi')
        
        try:
            # Process the file with FFmpeg if available
            if is_ffmpeg_installed():
                output_filename = process_audio_with_ffmpeg(file_path, effect)
                # Get the current year for copyright in footer
                now = datetime.now()
                return render_template('result.html', audio_file=output_filename, now=now)
            else:
                # Fallback to simulation if FFmpeg is not available
                flash('FFmpeg not detected. Using simulated audio processing.', 'warning')
                output_filename = simulate_audio_processing(file_path, effect)
                # Get the current year for copyright in footer
                now = datetime.now()
                return render_template('result.html', audio_file=output_filename, is_simulated=True, now=now)
        except Exception as e:
            flash(f'Error processing audio: {str(e)}. Using fallback method.', 'danger')
            # Fallback to simulation if processing fails
            output_filename = simulate_audio_processing(file_path, effect)
            # Get the current year for copyright in footer
            now = datetime.now()
            return render_template('result.html', audio_file=output_filename, is_simulated=True, now=now)
    
    flash('File type not allowed. Please upload an MP3, WAV, OGG, or M4A file.', 'danger')
    return redirect(url_for('index'))

@app.route('/custom_effect', methods=['POST'])
def custom_effect():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        # Save the uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Get custom effect parameters from JSON
        params = request.form.get('params', '{}')
        try:
            effect_params = json.loads(params)
        except json.JSONDecodeError:
            effect_params = {}
        
        try:
            if is_ffmpeg_installed():
                output_filename = process_custom_effect(file_path, effect_params)
                return jsonify({
                    'success': True,
                    'filename': output_filename,
                    'url': url_for('static', filename=f'uploads/{output_filename}')
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'FFmpeg not installed',
                    'simulated': True
                }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'File type not allowed'}), 400

def is_ffmpeg_installed():
    """Check if FFmpeg is installed and available in PATH"""
    try:
        cmd = [FFMPEG_PATH, '-version']
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def process_audio_with_ffmpeg(file_path, effect):
    """
    Process audio file using FFmpeg command-line tool
    """
    # Create output filename
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_filename = f"{effect}_{base_name}_{uuid.uuid4().hex[:8]}.mp3"
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
    
    # Choose the appropriate FFmpeg command based on the effect
    if effect == 'lofi':
        # Lo-Fi effect: improved with stronger lowpass filter, vinyl noise, more compression, and pitch shift
        cmd = [
            FFMPEG_PATH, '-i', file_path, 
            '-af', 'lowpass=2000,highpass=20,acompressor=threshold=0.1:ratio=3:attack=100:release=1000,volume=1.2,asetrate=44100*0.95,aresample=44100,tremolo=10:0.1,afftdn=nf=-20,vibrato=5:0.2',
            '-ar', '22050',  # Lower sample rate
            output_path
        ]
    elif effect == 'jazz':
        # Jazz effect: Enhanced with stronger mid frequencies, deeper reverb, swing feel
        cmd = [
            FFMPEG_PATH, '-i', file_path,
            '-af', 'equalizer=f=200:width_type=h:width=100:g=4,equalizer=f=1000:width_type=h:width=200:g=6,equalizer=f=400:width_type=h:width=100:g=3,aecho=0.9:0.8:60:0.5,aecho=0.6:0.4:30:0.3,areverse,aecho=0.3:0.3:10:0.3,areverse',
            output_path
        ]
    elif effect == 'dubstep':
        # Dubstep effect: Extreme bass boost, wobble effect, pulsing dynamics
        cmd = [
            FFMPEG_PATH, '-i', file_path,
            '-af', 'equalizer=f=60:width_type=h:width=50:g=8,equalizer=f=120:width_type=h:width=100:g=6,equalizer=f=7000:width_type=h:width=2000:g=-2,tremolo=5:0.9,acompressor=threshold=0.05:ratio=8:attack=3:release=50,volume=1.5',
            output_path
        ]
    elif effect == 'vaporwave':
        # Vaporwave effect: Slowed down, pitch shifted, reverb
        cmd = [
            FFMPEG_PATH, '-i', file_path,
            '-af', 'asetrate=44100*0.8,aresample=44100,atempo=0.8,aecho=0.8:0.8:1000:0.5,chorus=0.7:0.9:50:10:15:1,equalizer=f=60:width_type=h:width=50:g=4',
            output_path
        ]
    elif effect == 'rock':
        # Rock effect: Distortion, heavy compression, mid boost
        cmd = [
            FFMPEG_PATH, '-i', file_path,
            '-af', 'equalizer=f=80:width_type=h:width=50:g=3,equalizer=f=300:width_type=h:width=100:g=5,equalizer=f=2000:width_type=h:width=400:g=2,acompressor=threshold=0.05:ratio=9:attack=5:release=100:makeup=2,volume=1.3',
            output_path
        ]
    else:
        # Default: Just convert to mp3
        cmd = [FFMPEG_PATH, '-i', file_path, output_path]
    
    # Print the command for debugging
    print(f"Running FFmpeg command: {' '.join(cmd)}")
    
    # Run the FFmpeg command
    subprocess.run(cmd, check=True)
    
    return output_filename

def process_custom_effect(file_path, params):
    """
    Process audio with custom effect parameters
    params: Dictionary of effect parameters
    """
    # Create output filename with custom prefix
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_filename = f"custom_{base_name}_{uuid.uuid4().hex[:8]}.mp3"
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
    
    # Build the filter chain based on parameters
    filter_chain = []
    
    # Bass boost
    if 'bass' in params:
        bass_level = max(min(float(params['bass']), 10.0), -10.0)  # Clamp between -10 and 10
        if bass_level != 0:
            filter_chain.append(f"equalizer=f=80:width_type=h:width=50:g={bass_level}")
    
    # Treble adjustment
    if 'treble' in params:
        treble_level = max(min(float(params['treble']), 10.0), -10.0)  # Clamp between -10 and 10
        if treble_level != 0:
            filter_chain.append(f"equalizer=f=8000:width_type=h:width=1000:g={treble_level}")
    
    # Reverb
    if 'reverb' in params and params['reverb']:
        reverb_level = max(min(float(params['reverb']), 1.0), 0.0)  # Clamp between 0 and 1
        if reverb_level > 0:
            delay = int(100 + reverb_level * 900)  # 100ms to 1000ms depending on level
            filter_chain.append(f"aecho=0.8:{reverb_level}:{delay}:0.5")
    
    # Tempo adjustment
    if 'tempo' in params:
        tempo_factor = max(min(float(params['tempo']), 2.0), 0.5)  # Clamp between 0.5x and 2x
        if tempo_factor != 1.0:
            filter_chain.append(f"atempo={tempo_factor}")
    
    # Pitch shift
    if 'pitch' in params:
        pitch_shift = max(min(float(params['pitch']), 12), -12)  # Clamp between -12 and +12 semitones
        if pitch_shift != 0:
            # Convert semitones to rate factor: 2^(semitones/12)
            rate_factor = 2 ** (pitch_shift / 12)
            filter_chain.append(f"asetrate=44100*{rate_factor},aresample=44100")
    
    # Low pass filter
    if 'lowpass' in params and params['lowpass']:
        cutoff_freq = max(min(int(params['lowpass']), 20000), 200)  # Clamp between 200Hz and 20kHz
        filter_chain.append(f"lowpass={cutoff_freq}")
    
    # Compression
    if 'compression' in params and params['compression']:
        comp_level = max(min(float(params['compression']), 10.0), 1.0)  # Clamp between 1 and 10
        threshold = 0.2 - (comp_level * 0.02)  # 0.2 down to 0.0 as compression increases
        ratio = comp_level  # 1:1 up to 10:1
        filter_chain.append(f"acompressor=threshold={threshold}:ratio={ratio}:attack=20:release=100:makeup=2")
    
    # Volume adjustment at the end
    if 'volume' in params:
        volume_level = max(min(float(params['volume']), 2.0), 0.1)  # Clamp between 0.1 and 2.0
        if volume_level != 1.0:
            filter_chain.append(f"volume={volume_level}")
    
    # Build the final FFmpeg command
    cmd = [FFMPEG_PATH, '-i', file_path]
    
    if filter_chain:
        filter_str = ','.join(filter_chain)
        cmd.extend(['-af', filter_str])
    
    cmd.append(output_path)
    
    # Print the command for debugging
    print(f"Running custom FFmpeg command: {' '.join(cmd)}")
    
    # Run the FFmpeg command
    subprocess.run(cmd, check=True)
    
    return output_filename

def simulate_audio_processing(file_path, effect):
    """
    Fallback method that simulates audio processing without actual processing libraries.
    """
    # Create a unique output filename
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_filename = f"simulated_{effect}_{base_name}_{uuid.uuid4().hex[:8]}.mp3"
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
    
    # Copy the original file (no actual processing)
    shutil.copy(file_path, output_path)
    
    return output_filename

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/about')
def about():
    # Get the current year for copyright in footer
    now = datetime.now()
    return render_template('about.html', now=now)

@app.route('/custom')
def custom_page():
    # Get the current year for copyright in footer
    now = datetime.now()
    return render_template('custom.html', now=now)

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

if __name__ == '__main__':
    app.run(debug=True) 