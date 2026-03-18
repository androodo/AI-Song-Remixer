import io
import os
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class EmbedConfig:
    sample_rate: int = 16000
    max_seconds: float = 30.0
    n_mfcc: int = 20


def _run_ffmpeg_to_wav_bytes(input_path: str, ffmpeg_exe: str, sample_rate: int) -> bytes:
    """
    Decode arbitrary audio with ffmpeg into mono 16-bit PCM WAV bytes.
    """
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i",
        input_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "wav",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore")[:2000])
    return proc.stdout


def _load_audio_mono(input_path: str, cfg: EmbedConfig, ffmpeg_exe: Optional[str]) -> Tuple[np.ndarray, int]:
    """
    Load audio as float32 mono array in [-1, 1] with desired sample rate.
    Prefers soundfile; falls back to ffmpeg if needed/available.
    """
    try:
        import soundfile as sf  # optional

        audio, sr = sf.read(input_path, dtype="float32", always_2d=False)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1).astype(np.float32)
        if sr != cfg.sample_rate:
            # Lightweight resampling via linear interpolation
            ratio = cfg.sample_rate / float(sr)
            n = int(round(audio.shape[0] * ratio))
            x_old = np.linspace(0.0, 1.0, num=audio.shape[0], dtype=np.float32)
            x_new = np.linspace(0.0, 1.0, num=n, dtype=np.float32)
            audio = np.interp(x_new, x_old, audio).astype(np.float32)
            sr = cfg.sample_rate
        return audio, sr
    except Exception:
        if not ffmpeg_exe:
            raise

    wav_bytes = _run_ffmpeg_to_wav_bytes(input_path, ffmpeg_exe, cfg.sample_rate)
    try:
        import soundfile as sf  # optional

        audio, sr = sf.read(io.BytesIO(wav_bytes), dtype="float32", always_2d=False)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1).astype(np.float32)
        return audio, sr
    except Exception:
        # Last resort: write wav bytes to temp and try again
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name
        try:
            import soundfile as sf  # optional

            audio, sr = sf.read(tmp_path, dtype="float32", always_2d=False)
            if audio.ndim > 1:
                audio = np.mean(audio, axis=1).astype(np.float32)
            return audio, sr
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _mfcc_embedding(audio: np.ndarray, sr: int, cfg: EmbedConfig) -> np.ndarray:
    """
    Compute a compact embedding using MFCC statistics.

    This isn't "generative AI", but it is an embedding vector suitable for
    similarity search and retrieval-augmented parameter selection.
    """
    if sr != cfg.sample_rate:
        raise ValueError("Sample rate mismatch")

    max_len = int(cfg.sample_rate * cfg.max_seconds)
    if audio.shape[0] > max_len:
        audio = audio[:max_len]

    # Ensure non-empty
    if audio.size < cfg.sample_rate // 4:
        raise ValueError("Audio too short")

    try:
        from python_speech_features import mfcc  # optional
    except Exception as e:
        raise RuntimeError(
            "Missing dependency python_speech_features. Install optional AI deps."
        ) from e

    feats = mfcc(
        audio,
        samplerate=sr,
        numcep=cfg.n_mfcc,
        nfft=1024,
        winlen=0.025,
        winstep=0.010,
        preemph=0.97,
        appendEnergy=True,
    ).astype(np.float32)

    mean = feats.mean(axis=0)
    std = feats.std(axis=0)
    emb = np.concatenate([mean, std], axis=0).astype(np.float32)

    # Add a few global stats (loudness-ish + zero-crossing-ish)
    rms = float(np.sqrt(np.mean(np.square(audio), dtype=np.float64)))
    zcr = float(np.mean(audio[:-1] * audio[1:] < 0.0))
    emb = np.concatenate([emb, np.array([rms, zcr], dtype=np.float32)], axis=0)

    # L2 normalize for cosine similarity
    norm = np.linalg.norm(emb) + 1e-12
    return (emb / norm).astype(np.float32)


def embed_audio_file(
    input_path: str,
    *,
    ffmpeg_exe: Optional[str] = None,
    cfg: Optional[EmbedConfig] = None,
) -> np.ndarray:
    cfg = cfg or EmbedConfig()
    audio, sr = _load_audio_mono(input_path, cfg, ffmpeg_exe)
    return _mfcc_embedding(audio, sr, cfg)

