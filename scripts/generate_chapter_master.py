"""
generate_chapter_master.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
《禅阅》经文音频生成与物理时间轴绝对对齐全自动流水线
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
用法:
    python scripts/generate_chapter_master.py jingangjing chapter_3
    python scripts/generate_chapter_master.py xinjing chapter_1
"""

import os
import sys
import json
import base64
import wave
import time
import subprocess
import soundfile as sf
import numpy as np
from scipy.ndimage import uniform_filter1d
from google import genai
from google.genai import types

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POEM_ENV = "d:/Projects/poem_project/.env"

def get_api_key():
    env_local = os.path.join(PROJECT_ROOT, ".env")
    for env_path in [env_local, POEM_ENV]:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("GEMINI_API_KEY", "")

# 严谨古汉语及梵音字音强制校正词典（与屏幕拼音注音 100% 同步）
PHONETIC_REPLACEMENTS = [
    # 心经
    ("波罗蜜多故", "波罗蜜哆故"), # duō 一声
    ("菩提萨婆诃", "菩提萨婆诃"), # sà 四声
    ("诸法空相", "诸法空向"),     # xiàng 四声
    ("无明尽", "无明进"),         # jìn 四声
    ("老死尽", "老死进"),         # jìn 四声
    ("阿耨多罗", "阿漏多罗"),     # ā nòu
    ("三藐", "三秒"),             # sān miǎo
    # 金刚经
    ("著衣持钵", "浊衣持钵"),     # zhuó 二声
    ("着衣持钵", "浊衣持钵"),     # zhuó 二声
    ("一时", "意时"),             # yì 四声
    ("祇树给孤独园", "奇树几孤独园"), # qí shù jǐ
    ("饭食讫", "饭食气"),         # qì 四声
    ("长老须菩提", "掌老须菩提"), # zhǎng 三声
    ("右膝着地", "右膝浊地"),     # zhuó 二声
    ("愿乐欲闻", "愿要欲闻"),     # yào 四声
    ("降伏其心", "降服其心"),     # xiáng fú
]

SANCTUARY_PLUS_FILTER = (
    "highpass=f=70,"
    "equalizer=f=150:width_type=h:width=120:g=2.2,"
    "equalizer=f=10500:width_type=h:width=2500:g=2.8,"
    "aecho=0.80:0.75:80|160|260:0.22|0.12|0.06"
)

def apply_phonetic_fixes(text: str) -> str:
    res = text
    for old_w, new_w in PHONETIC_REPLACEMENTS:
        res = res.replace(old_w, new_w)
    return res

def synthesize_voice(client, voice_name: str, text: str, out_mp3: str) -> bool:
    prompt = f"用平稳、自然、无修饰的普通话念读以下文字，语调平平、不带朗诵感：\n\n{text}"
    raw_wav = out_mp3 + ".raw.wav"

    print(f"🎙️ 正在合成【{voice_name}】-> {out_mp3}...", flush=True)

    for attempt in range(1, 4):
        try:
            res = client.models.generate_content(
                model="gemini-3.1-flash-tts-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                        )
                    )
                )
            )
            cand = res.candidates[0]
            if cand.content and cand.content.parts:
                pcm = cand.content.parts[0].inline_data.data
                if isinstance(pcm, str):
                    pcm = base64.b64decode(pcm)
                with wave.open(raw_wav, "wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000)
                    wf.writeframes(pcm)

                tmp_wav = out_mp3 + ".tmp.wav"
                subprocess.run([
                    "ffmpeg", "-y", "-i", raw_wav.replace('\\', '/'),
                    "-af", SANCTUARY_PLUS_FILTER,
                    "-c:a", "pcm_s16le", tmp_wav.replace('\\', '/')
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                subprocess.run([
                    "ffmpeg", "-y", "-i", tmp_wav.replace('\\', '/'),
                    "-b:a", "192k", out_mp3.replace('\\', '/')
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                if os.path.exists(raw_wav): os.remove(raw_wav)
                if os.path.exists(tmp_wav): os.remove(tmp_wav)
                print(f"   ✅ 合成完成: {out_mp3}", flush=True)
                return True
            else:
                print(f"   ⚠️ 尝试 {attempt} 返回空，等待 15s...", flush=True)
                time.sleep(15)
        except Exception as e:
            print(f"   ⚠️ 尝试 {attempt} 异常: {e}，等待 25s...", flush=True)
            time.sleep(25)
    return False

def align_json_to_audio_bursts(audio_path: str, json_path: str):
    print(f"📐 正在运行 1:1 声学物理爆发点检测与时间轴校准...", flush=True)
    data, sr = sf.read(audio_path)
    if data.ndim == 2:
        data = data.mean(axis=1)

    frame_len = int(sr * 0.02)
    hop_len = int(sr * 0.01)
    energy = np.array([np.sum(data[i:i+frame_len]**2) for i in range(0, len(data) - frame_len, hop_len)])
    times = np.arange(len(energy)) * 0.01

    energy_smooth = uniform_filter1d(energy, size=20)
    thresh = np.percentile(energy_smooth, 26)

    speech = energy_smooth > thresh
    bursts = []
    in_burst = False
    b_start = 0

    for t, is_sp in zip(times, speech):
        if is_sp and not in_burst:
            in_burst = True
            b_start = t
        elif not is_sp and in_burst:
            in_burst = False
            if t - b_start >= 0.30:
                bursts.append((round(b_start, 2), round(t, 2)))

    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    paragraphs = doc["paragraphs"]
    burst_idx = 0

    for p_idx, p in enumerate(paragraphs):
        p["id"] = p_idx + 1
        lines = p.get("lines", [])
        if not lines: continue

        for l in lines:
            if burst_idx < len(bursts):
                b_st, b_et = bursts[burst_idx]
                l["lineStart"] = round(b_st, 3)
                l["lineEnd"] = round(b_et, 3)

                chars = l.get("chars", [])
                valid_chars = [c for c in chars if c.get("text", "").strip() and c.get("text") not in "，。！？；：、"]
                c_dur = (b_et - b_st) / max(1, len(valid_chars))
                c_t = b_st
                for c in chars:
                    if c.get("text", "").strip() and c.get("text") not in "，。！？；：、":
                        c["startTime"] = round(c_t, 3)
                        c["endTime"] = round(c_t + c_dur, 3)
                        c_t += c_dur
                burst_idx += 1

        p["startTime"] = lines[0]["lineStart"]
        p["endTime"] = lines[-1]["lineEnd"]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    print(f"✅ 时间轴校准完成！总行数: {burst_idx}, 音频时长: {len(data)/sr:.2f}s")

def build_chapter(book_id: str, chapter_id: str):
    api_key = get_api_key()
    if not api_key:
        print("❌ 未找到 GEMINI_API_KEY！")
        return

    client = genai.Client(api_key=api_key)

    json_path = os.path.join(PROJECT_ROOT, "src", "data", book_id, f"{chapter_id}.json")
    if not os.path.exists(json_path):
        print(f"❌ 找不到经文 JSON: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    # 提取纯文本并进行发音校准
    raw_lines = []
    for p in doc.get("paragraphs", []):
        for l in p.get("lines", []):
            line_txt = "".join(c.get("text", "") for c in l.get("chars", []))
            raw_lines.append(line_txt)

    full_text = "".join(raw_lines)
    fixed_text = apply_phonetic_fixes(full_text)

    # 准备输出目录与文件路径
    audio_dir = os.path.join(PROJECT_ROOT, "public", "audio", book_id if book_id != "xinjing" else "")
    os.makedirs(audio_dir, exist_ok=True)

    base_name = f"{chapter_id}" if book_id != "xinjing" else "xinjing"
    female_mp3 = os.path.join(audio_dir, f"{base_name}_female.mp3")
    male_mp3 = os.path.join(audio_dir, f"{base_name}_male.mp3")
    default_mp3 = os.path.join(audio_dir, f"{base_name}.mp3")

    print(f"\n=======================================================")
    print(f"📖 正在为【{book_id} / {chapter_id}】构建双音色母带流水线...")
    print(f"=======================================================")

    # 1. 生成女声 (Zephyr)
    synthesize_voice(client, "Zephyr", fixed_text, female_mp3)
    time.sleep(15)

    # 2. 生成男声 (Charon)
    synthesize_voice(client, "Charon", fixed_text, male_mp3)

    # 3. 部署默认 MP3
    if os.path.exists(female_mp3):
        with open(female_mp3, "rb") as f_in, open(default_mp3, "wb") as f_out:
            f_out.write(f_in.read())

    # 4. 1:1 声学物理爆发点对齐
    align_json_to_audio_bursts(female_mp3, json_path)
    print(f"🎉 【{book_id} / {chapter_id}】全套母带与对齐就绪！\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python scripts/generate_chapter_master.py <book_id> <chapter_id>")
        print("示例: python scripts/generate_chapter_master.py jingangjing chapter_3")
        sys.exit(1)
    build_chapter(sys.argv[1], sys.argv[2])
