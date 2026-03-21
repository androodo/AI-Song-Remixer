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
from typing import Optional

def get_ffmpeg_exe() -> Optional[str]:
    """
    Resolve ffmpeg executable path.
    Preference order:
    1) env var FFMPEG_PATH (full path)
    2) ffmpeg on PATH
    3) common Windows locations (Downloads extracts, C:\\ffmpeg)
    """
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    from shutil import which

    on_path = which("ffmpeg")
    if on_path:
        return on_path

    # Common locations (keep this fast + conservative)
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        os.path.join(os.environ.get("USERPROFILE", ""), "Downloads", "ffmpeg", "bin", "ffmpeg.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c

    # Last resort: scan Downloads for a typical extract layout: */bin/ffmpeg.exe
    try:
        import glob

        dl = os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")
        if dl and os.path.isdir(dl):
            matches = glob.glob(os.path.join(dl, "**", "bin", "ffmpeg.exe"), recursive=True)
            for m in matches[:10]:
                if os.path.exists(m):
                    return m
    except Exception:
        pass

    return None


FFMPEG_EXE = get_ffmpeg_exe()

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


def save_uploaded_file(file_storage, *, prefix: str) -> str:
    """
    Save an uploaded file to UPLOAD_FOLDER with a unique name.
    Returns absolute path to the saved file.
    """
    orig_name = secure_filename(file_storage.filename or "upload")
    base, ext = os.path.splitext(orig_name)
    if not ext:
        ext = ".bin"
    unique_name = f"{prefix}_{base}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file_storage.save(file_path)
    return file_path

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
        # Save the uploaded file (unique name to prevent collisions/caching confusion)
        file_path = save_uploaded_file(file, prefix="upload")
        
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
            flash(f'Error processing audio: {str(e)}. Using fallback method (simulated copy).', 'danger')
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
        # Save the uploaded file (unique name)
        file_path = save_uploaded_file(file, prefix="custom_in")
        
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


@app.route('/recommend', methods=['POST'])
def recommend_effect():
    """
    Offline "AI recommend": computes an embedding for the uploaded audio and retrieves
    the closest match from a local reference index (if present).
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400

    if not (file and allowed_file(file.filename)):
        return jsonify({'success': False, 'error': 'File type not allowed'}), 400

    # Save uploaded file (unique name to avoid collisions)
    orig_name = secure_filename(file.filename)
    file_path = save_uploaded_file(file, prefix="ai")

    from audio_ai.embed import embed_audio_file
    from audio_ai.index import load_index, recommend_from_index

    try:
        query = embed_audio_file(file_path, ffmpeg_exe=FFMPEG_EXE)
    except Exception as e:
        note = None
        ext = os.path.splitext(orig_name)[1].lower()
        if not FFMPEG_EXE and ext in {'.mp3', '.m4a', '.aac'}:
            note = "FFmpeg is required to analyze MP3/M4A for AI Recommend. Install FFmpeg or upload WAV/OGG."
        payload = {'success': False, 'error': str(e)}
        if note:
            payload['note'] = note
        return jsonify(payload), 400

    idx = load_index()
    if idx is None:
        # Heuristic fallback if user hasn't built an index yet
        return jsonify(
            {
                'success': True,
                'effect': 'lofi',
                'params': {},
                'confidence': 0.0,
                'note': 'No local index found. Add reference clips to reference_audio/ and run: python -m audio_ai.build_index',
            }
        )

    rec = recommend_from_index(query, idx, k=5)
    return jsonify({'success': True, **rec})


@app.route('/chat_suggestions', methods=['POST'])
def chat_suggestions():
    """
    LangChain-powered helper that explains the current settings and suggests tweaks.

    This expects an LLM API key (e.g. OPENAI_API_KEY) to be configured in the environment.
    """
    try:
        data = request.get_json(force=True, silent=False) or {}
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid JSON payload'}), 400

    question = str(data.get('question') or '').strip()
    effect = str(data.get('effect') or 'lofi')
    params = data.get('params') or {}

    if not question:
        question = "Help me pick better settings for this song."

    try:
        from lang_assistant import suggest_parameters
    except Exception as e:
        return jsonify({'success': False, 'error': f'LangChain not available: {e}'}), 500

    try:
        answer = suggest_parameters(question=question, effect=effect, params=params)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    return jsonify({'success': True, 'answer': answer})

def is_ffmpeg_installed():
    """Check if FFmpeg is installed and available in PATH"""
    try:
        if not FFMPEG_EXE:
            return False
        cmd = [FFMPEG_EXE, '-version']
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
    
    # Make each remix audibly distinct: small per-run variation
    rnd = random.Random(uuid.uuid4().int & 0xFFFFFFFF)

    # Common encoding settings (consistent output + avoid "it didn't change" from weird passthrough)
    base_cmd = [FFMPEG_EXE, "-y", "-hide_banner", "-i", file_path]
    out_args = ["-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100"]

    # Choose the appropriate FFmpeg command based on the effect
    if effect == 'lofi':
        # More obvious Lo-Fi: band-limit, bitcrush, wow/flutter, compression
        # (Avoids mixing synthetic noise sources that can accidentally extend duration.)
        cutoff = int(rnd.uniform(1500, 2600))
        trem_f = rnd.uniform(6.0, 11.0)
        trem_d = rnd.uniform(0.08, 0.18)
        vib_f = rnd.uniform(3.0, 6.0)
        vib_d = rnd.uniform(0.15, 0.35)
        pitch = rnd.uniform(0.92, 0.97)
        crush_bits = int(rnd.choice([5, 6, 7]))
        af = (
            f"highpass=30,lowpass={cutoff},"
            f"asetrate=44100*{pitch:.4f},aresample=44100,"
            f"acrusher=bits={crush_bits}:mode=log:mix=0.60,"
            f"tremolo=f={trem_f:.2f}:d={trem_d:.3f},"
            f"vibrato=f={vib_f:.2f}:d={vib_d:.3f},"
            "acompressor=threshold=0.08:ratio=4:attack=20:release=250:makeup=2,"
            "alimiter=limit=0.95,volume=1.15"
        )
        cmd = base_cmd + ["-af", af] + out_args + [output_path]
    elif effect == 'jazz':
        # Jazz-ish: mid-forward tone, gentle saturation (via comp), roomy echo layers, subtle chorus
        room = int(rnd.uniform(35, 70))
        chorus_d = rnd.uniform(0.3, 0.6)
        tempo = rnd.uniform(0.98, 1.02)
        af = (
            "highpass=25,"
            "equalizer=f=180:width_type=h:width=120:g=3,"
            "equalizer=f=900:width_type=h:width=300:g=4,"
            "equalizer=f=3500:width_type=h:width=1200:g=-1,"
            f"chorus=0.6:0.8:{room}:{room/2:.1f}:{room/3:.1f}:{chorus_d:.2f},"
            "aecho=0.85:0.6:80:0.25,aecho=0.6:0.4:35:0.18,"
            f"atempo={tempo:.3f},"
            "acompressor=threshold=0.12:ratio=2.5:attack=15:release=180:makeup=1.2,"
            "alimiter=limit=0.95,volume=1.10"
        )
        cmd = base_cmd + ["-af", af] + out_args + [output_path]
    elif effect == 'dubstep':
        # Dubstep: big sub + wobble + hard comp/limiting
        wob_f = rnd.uniform(2.5, 6.5)
        wob_d = rnd.uniform(0.65, 0.95)
        bass_g = rnd.uniform(7.0, 11.0)
        af = (
            "highpass=25,"
            f"equalizer=f=55:width_type=h:width=40:g={bass_g:.1f},"
            "equalizer=f=110:width_type=h:width=80:g=6,"
            "equalizer=f=7500:width_type=h:width=2500:g=-3,"
            f"tremolo=f={wob_f:.2f}:d={wob_d:.2f},"
            "acompressor=threshold=0.05:ratio=10:attack=2:release=60:makeup=3,"
            "alimiter=limit=0.93,volume=1.30"
        )
        cmd = base_cmd + ["-af", af] + out_args + [output_path]
    elif effect == 'vaporwave':
        # Vaporwave: slow down + slight pitch down, but avoid harsh artifacts.
        # We decouple tempo (T) and pitch (P) using: asetrate=P then atempo=T/P.
        # This keeps the "vapor" vibe without double-slowing or extreme pitch shifts.
        target_tempo = rnd.uniform(0.84, 0.92)  # overall slowdown
        pitch = rnd.uniform(0.90, 0.96)  # pitch-down (mild)
        atempo = max(min(target_tempo / pitch, 2.0), 0.5)
        echo_d = int(rnd.uniform(520, 820))
        echo_decay = rnd.uniform(0.20, 0.32)
        chorus_depth = rnd.uniform(0.7, 1.05)
        af = (
            f"asetrate=44100*{pitch:.4f},aresample=44100:resampler=soxr:precision=28,"
            f"atempo={atempo:.3f},"
            "highpass=25,lowpass=8500,"
            "equalizer=f=120:width_type=h:width=120:g=2.0,"
            "equalizer=f=3000:width_type=h:width=1800:g=-1.2,"
            f"chorus=0.55:0.8:40:8:12:{chorus_depth:.2f},"
            f"aecho=0.70:0.35:{echo_d}:{echo_decay:.2f},"
            "dynaudnorm=f=200:g=5,"
            "alimiter=limit=0.95,volume=1.05"
        )
        cmd = base_cmd + ["-af", af] + out_args + [output_path]
    elif effect == 'rock':
        # Rock: presence boost + stronger compression + a touch of grit via bitcrush mix
        crush_mix = rnd.uniform(0.18, 0.35)
        af = (
            "highpass=35,"
            "equalizer=f=95:width_type=h:width=70:g=2.5,"
            "equalizer=f=320:width_type=h:width=140:g=3.5,"
            "equalizer=f=2300:width_type=h:width=600:g=2.5,"
            "equalizer=f=6000:width_type=h:width=2500:g=1.8,"
            f"acrusher=bits=8:mode=log:mix={crush_mix:.2f},"
            "acompressor=threshold=0.06:ratio=7:attack=5:release=120:makeup=2.2,"
            "alimiter=limit=0.92,volume=1.18"
        )
        cmd = base_cmd + ["-af", af] + out_args + [output_path]
    else:
        cmd = base_cmd + out_args + [output_path]
    
    # Print the command for debugging
    print(f"Running FFmpeg command: {' '.join(cmd)}")
    
    # Run the FFmpeg command (capture stderr for meaningful failures)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="ignore")[:2000]
        raise RuntimeError(f"FFmpeg failed (exit {proc.returncode}): {err}")
    
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
    
    # Reverb (short room-like echo instead of obvious "second copy")
    if 'reverb' in params and params['reverb']:
        reverb_level = max(min(float(params['reverb']), 1.0), 0.0)  # 0 to 1
        if reverb_level > 0:
            # Keep delay short (40–160ms) so it feels like space, not a second track.
            delay = int(40 + reverb_level * 120)
            out_gain = 0.25 + reverb_level * 0.25  # 0.25–0.5
            decay = 0.25 + reverb_level * 0.25     # 0.25–0.5
            filter_chain.append(f"aecho=0.8:{out_gain}:{delay}:{decay}")
    
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
    cmd = [FFMPEG_EXE, '-i', file_path]
    
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
    # Bind to public interface for hosting (e.g., AWS EC2 behind a reverse proxy).
    # Default debug is off for production safety; enable via DEBUG=1.
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    debug_flag = os.environ.get("DEBUG", "false").strip().lower()
    debug = debug_flag in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)