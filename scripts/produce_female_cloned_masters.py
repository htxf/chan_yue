import os
import sys
import shutil
import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import gaussian_filter1d
import subprocess
from pydub import AudioSegment

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from scripts.generate_sutra_master import generate_sutra_master

REF_PATH = os.path.join(PROJECT_ROOT, "public", "audio", "compare", "reference_user_sample.mp3")

def morph_audio_timbre(audio_path: str, ref_path: str):
    """
    在频域应用参考范本的声学共振峰包络与微空间，时长严格不变（毫秒级时间戳100%保持不变）
    """
    print(f"🎨 正在对 [{os.path.basename(audio_path)}] 进行真实诵经共振峰声学移植...", flush=True)
    ref_seg = AudioSegment.from_file(ref_path).set_channels(1).set_frame_rate(24000)
    src_seg = AudioSegment.from_file(audio_path).set_channels(1).set_frame_rate(24000)

    ref_arr = np.array(ref_seg.get_array_of_samples(), dtype=np.float32) / 32768.0
    src_arr = np.array(src_seg.get_array_of_samples(), dtype=np.float32) / 32768.0

    sr = 24000
    n_fft = 2048
    hop = 512

    _, _, Zxx_ref = signal.stft(ref_arr, fs=sr, nperseg=n_fft, noverlap=n_fft - hop)
    _, _, Zxx_src = signal.stft(src_arr, fs=sr, nperseg=n_fft, noverlap=n_fft - hop)

    spec_ref = np.mean(np.abs(Zxx_ref), axis=1) + 1e-6
    spec_src = np.mean(np.abs(Zxx_src), axis=1) + 1e-6

    gain_curve = spec_ref / spec_src
    gain_curve_smooth = gaussian_filter1d(gain_curve, sigma=10)
    gain_curve_smooth = np.clip(gain_curve_smooth, 0.3, 3.2)

    Zxx_morphed = Zxx_src * gain_curve_smooth[:, np.newaxis]
    _, morphed_arr = signal.istft(Zxx_morphed, fs=sr, nperseg=n_fft, noverlap=n_fft - hop)

    orig_len = len(src_arr)
    morphed_arr = morphed_arr[:orig_len]

    max_val = np.max(np.abs(morphed_arr)) + 1e-8
    morphed_arr = (morphed_arr / max_val) * 0.85

    tmp_wav = audio_path + ".tmp.wav"
    sf.write(tmp_wav, morphed_arr, sr)

    out_tmp_mp3 = audio_path + ".morphed.mp3"
    cmd = [
        "ffmpeg", "-y", "-i", tmp_wav.replace('\\', '/'),
        "-af", "equalizer=f=160:width_type=h:width=100:g=2.8,equalizer=f=3400:width_type=h:width=1200:g=-2.2,aecho=0.88:0.72:60|120:0.18|0.08",
        "-b:a", "160k",
        out_tmp_mp3.replace('\\', '/')
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if os.path.exists(tmp_wav):
        os.remove(tmp_wav)

    if res.returncode == 0 and os.path.exists(out_tmp_mp3):
        os.replace(out_tmp_mp3, audio_path)
        print(f"✨ [{os.path.basename(audio_path)}] 声学共鸣移植完成！", flush=True)
    else:
        print(f"⚠️ FFmpeg 后处理失败，保留原干声: {res.stderr.decode('utf-8', errors='ignore')}", flush=True)


def build_chapter(book: str, chapter: str, audio_primary: str, audio_female: str):
    print(f"\n==================================================", flush=True)
    print(f"🚀 开始生成: {book} -> {chapter}", flush=True)
    print(f"==================================================", flush=True)

    # 1. 调用 Azure 动态生成高保真干音 + 提取毫秒级时间戳并回写 JSON
    generate_sutra_master(
        book=book,
        chapter=chapter,
        voice="xiaoqiu",
        rate="-11%",
        output=audio_primary,
        update_json=True,
        voice_key="female"
    )

    # 2. 实施真实录音声学声纹共振峰克隆
    morph_audio_timbre(audio_primary, REF_PATH)

    # 3. 复制给 _female.mp3 确保单品与显式切换完全一致
    shutil.copyfile(audio_primary, audio_female)
    print(f"💾 已同步复制到: {audio_female}", flush=True)


def main():
    targets = [
        # 1. 心经全篇
        ("xinjing", "chapter_1",
         os.path.join(PROJECT_ROOT, "public", "audio", "xinjing.mp3"),
         os.path.join(PROJECT_ROOT, "public", "audio", "xinjing_female.mp3")),
        # 2. 金刚经第一品
        ("jingangjing", "chapter_1",
         os.path.join(PROJECT_ROOT, "public", "audio", "jingangjing", "chapter_1.mp3"),
         os.path.join(PROJECT_ROOT, "public", "audio", "jingangjing", "chapter_1_female.mp3")),
        # 3. 金刚经第二品
        ("jingangjing", "chapter_2",
         os.path.join(PROJECT_ROOT, "public", "audio", "jingangjing", "chapter_2.mp3"),
         os.path.join(PROJECT_ROOT, "public", "audio", "jingangjing", "chapter_2_female.mp3")),
        # 4. 金刚经第三品
        ("jingangjing", "chapter_3",
         os.path.join(PROJECT_ROOT, "public", "audio", "jingangjing", "chapter_3.mp3"),
         os.path.join(PROJECT_ROOT, "public", "audio", "jingangjing", "chapter_3_female.mp3")),
    ]

    for book, chapter, p_main, p_fem in targets:
        build_chapter(book, chapter, p_main, p_fem)

    print("\n🎉 全部 4 篇女声母带生成、时间轴回写与声纹克隆完成！", flush=True)

if __name__ == "__main__":
    main()
