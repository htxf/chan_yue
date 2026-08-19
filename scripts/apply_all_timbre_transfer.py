import os
import sys
import soundfile as sf
import numpy as np
import librosa
import scipy.signal as signal
from scipy.ndimage import gaussian_filter1d
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = "d:/Projects/chan_yue"
SAMPLE_PATH = os.path.join(PROJECT_ROOT, "sample.wav")

SANCTUARY_PLUS_FILTER = (
    "highpass=f=70,"
    "equalizer=f=150:width_type=h:width=120:g=2.2,"
    "equalizer=f=10500:width_type=h:width=2500:g=2.8,"
    "aecho=0.80:0.75:80|160|260:0.22|0.12|0.06"
)

def transfer_timbre(target_ref_path, src_audio_path, out_mp3_path, semitones=4.7):
    print(f"--> Transferring timbre to: {out_mp3_path}...", flush=True)
    ref_data, ref_sr = sf.read(target_ref_path)
    if ref_data.ndim == 2:
        ref_data = ref_data.mean(axis=1)

    src_data, src_sr = sf.read(src_audio_path)
    if src_data.ndim == 2:
        src_data = src_data.mean(axis=1)

    orig_len = len(src_data)

    # 1. Pitch shift to match target register
    shifted_audio = librosa.effects.pitch_shift(src_data, sr=src_sr, n_steps=semitones)

    # 2. Spectral envelope transfer
    n_fft = 2048
    hop_length = 512
    ref_resampled = librosa.resample(ref_data, orig_sr=ref_sr, target_sr=src_sr)
    S_ref = np.abs(librosa.stft(ref_resampled, n_fft=n_fft, hop_length=hop_length))
    mean_spec_ref = np.mean(S_ref, axis=1) + 1e-8

    S_src = np.abs(librosa.stft(shifted_audio, n_fft=n_fft, hop_length=hop_length))
    mean_spec_src = np.mean(S_src, axis=1) + 1e-8

    gain_curve = np.sqrt(mean_spec_ref / mean_spec_src)
    gain_curve_smooth = gaussian_filter1d(gain_curve, sigma=12)
    gain_curve_smooth = np.clip(gain_curve_smooth, 0.35, 2.8)

    D_src = librosa.stft(shifted_audio, n_fft=n_fft, hop_length=hop_length)
    D_matched = D_src * gain_curve_smooth[:, np.newaxis]
    morphed_audio = librosa.istft(D_matched, hop_length=hop_length, length=orig_len)

    # Peak normalize
    morphed_audio = morphed_audio / (np.max(np.abs(morphed_audio)) + 1e-8) * 0.88

    tmp_wav = out_mp3_path + ".tmp.wav"
    sf.write(tmp_wav, morphed_audio, src_sr)

    cmd = [
        "ffmpeg", "-y", "-i", tmp_wav.replace('\\', '/'),
        "-af", SANCTUARY_PLUS_FILTER,
        "-b:a", "192k",
        out_mp3_path.replace('\\', '/')
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if os.path.exists(tmp_wav):
        os.remove(tmp_wav)

    print(f"✅ Successfully transferred timbre: {out_mp3_path} (Duration: {orig_len/src_sr:.2f}s)", flush=True)

def main():
    # 1. Morph Chapter 1
    transfer_timbre(
        SAMPLE_PATH,
        os.path.join(PROJECT_ROOT, "public", "audio", "jingangjing", "chapter_1.mp3"),
        os.path.join(PROJECT_ROOT, "public", "audio", "jingangjing", "chapter_1.mp3")
    )

    # 2. Morph Heart Sutra
    transfer_timbre(
        SAMPLE_PATH,
        os.path.join(PROJECT_ROOT, "public", "audio", "xinjing.mp3"),
        os.path.join(PROJECT_ROOT, "public", "audio", "xinjing.mp3")
    )

if __name__ == "__main__":
    main()
