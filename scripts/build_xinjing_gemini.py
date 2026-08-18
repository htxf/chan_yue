"""
build_xinjing_gemini.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
《心经》分段高保真诵读生成引擎（Google Gemini 3.1 Flash TTS + 1.5x古刹幽鸣）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import json
import time
import base64
import wave
import subprocess
import soundfile as sf
import numpy as np
from google import genai
from google.genai import types

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(PROJECT_ROOT, "scripts"))
from buddhist_dict import clean_tts_text

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

TTS_MODEL = "gemini-3.1-flash-tts-preview"
TTS_VOICE = "Fenrir"
TTS_SAMPLE_RATE = 24000

SANCTUARY_PLUS_FILTER = (
    "highpass=f=70,"
    "equalizer=f=150:width_type=h:width=120:g=2.2,"
    "equalizer=f=10500:width_type=h:width=2500:g=2.8,"
    "aecho=0.80:0.75:80|160|260:0.22|0.12|0.06"
)

def pcm_bytes_to_wav(pcm_bytes: bytes, sample_rate=24000, channels=1, sample_width=2) -> bytes:
    import io
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()

def apply_sanctuary_filter(raw_wav_path: str, out_wav_path: str):
    tmp = out_wav_path + ".tmp.wav"
    cmd = [
        'ffmpeg', '-y', '-i', raw_wav_path.replace('\\', '/'),
        '-af', SANCTUARY_PLUS_FILTER,
        '-c:a', 'pcm_s16le', tmp.replace('\\', '/')
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and os.path.exists(tmp):
        if os.path.exists(out_wav_path):
            os.remove(out_wav_path)
        os.rename(tmp, out_wav_path)
    else:
        import shutil
        shutil.copy(raw_wav_path, out_wav_path)

XINJING_PARTS = [
    # 前半段（第1~15段）：照见五蕴皆空至无智亦无得
    (
        0, 15,
        "观自在菩萨，行深波惹波罗蜜多时，照见五蕴皆空，度一切苦厄。"
        "赦利子，色不异空，空不异色，色即是空，空即是色，受想行识，亦复如是。"
        "赦利子，是诸法空向，不生不灭，不垢不净，不增不减。"
        "是故空中无色，无受想行识，无眼耳鼻舌身意，无色声香味触法，无眼界，乃至无意识界。"
        "无无明，亦无无明进，乃至无老死，亦无老死进。无苦集灭道，无智亦无得。"
    ),
    # 后半段（第16~27段）：以无所得故至菩提萨婆诃
    (
        15, 27,
        "以无所得故，菩提萨垛，衣波惹波罗蜜多故，心无挂碍；"
        "无挂碍故，无有恐怖，远离颠倒梦想，究竟涅盘。"
        "三世诸佛，衣波惹波罗蜜多故，得锕漏多罗三秒三菩提。"
        "故知波惹波罗蜜多，是大神咒，是大明咒，是无上咒，是无等等咒，能除一切苦，真实不虚。"
        "故说波惹波罗蜜多咒，即说咒曰：阶谛阶谛，波罗阶谛，波罗僧阶谛，菩提娑婆喝。"
    )
]

def synthesize_text(client, text: str) -> np.ndarray:
    prompt = (
        "请用沉着、平和、清晰、从容的标准普通话朗读以下经文，"
        "语调自然平稳，字音准确，不急不缓，字字分明：\n\n"
        f"{text}"
    )
    res = client.models.generate_content(
        model=TTS_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=TTS_VOICE
                    )
                )
            )
        )
    )
    cand = res.candidates[0]
    pcm = cand.content.parts[0].inline_data.data
    if isinstance(pcm, str):
        pcm = base64.b64decode(pcm)
    wav_bytes = pcm_bytes_to_wav(pcm, sample_rate=TTS_SAMPLE_RATE)
    
    # 读回为 numpy
    import io
    data, sr = sf.read(io.BytesIO(wav_bytes), dtype='float32')
    return data

def main():
    api_key = get_api_key()
    if not api_key:
        print("❌ 未找到 GEMINI_API_KEY！")
        sys.exit(1)

    client = genai.Client(api_key=api_key, http_options={'timeout': 180000})
    json_path = os.path.join(PROJECT_ROOT, "src", "data", "xinjing", "chapter_1.json")

    full_xinjing_text = (
        "观自在菩萨，行深波惹波罗蜜多时，照见五蕴皆空，度一切苦厄。"
        "赦利子，色不异空，空不异色，色即是空，空即是色，受想行识，亦复如是。"
        "赦利子，是诸法空向，不生不灭，不垢不净，不增不减。"
        "是故空中无色，无受想行识，无眼耳鼻舌身意，无色声香味触法，无眼界，乃至无意识界。"
        "无无明，亦无无明进，乃至无老死，亦无老死进。无苦集灭道，无智亦无得。"
        "以无所得故，菩提萨垛，衣波惹波罗蜜多故，心无挂碍；"
        "无挂碍故，无有恐怖，远离颠倒梦想，究竟涅盘。"
        "三世诸佛，衣波惹波罗蜜多故，得锕漏多罗三秒三菩提。"
        "故知波惹波罗蜜多，是大神咒，是大明咒，是无上咒，是无等等咒，能除一切苦，真实不虚。"
        "故说波惹波罗蜜多咒，即说咒曰：阶谛阶谛，波罗阶谛，波罗僧阶谛，菩提娑婆喝。"
    )

    print("==================================================", flush=True)
    print("📖 正在全篇单次连续生成《般若波罗蜜多心经》（Gemini 3.1 Flash TTS Fenrir 版）...", flush=True)
    print(f"   经文字数: {len(full_xinjing_text)} 字", flush=True)
    print("==================================================", flush=True)

    t0 = time.time()
    prompt = (
        "请用沉着、平和、清晰、从容的标准普通话朗读以下经文，"
        "语调自然平稳，字音准确，不急不缓，字字分明：\n\n"
        f"{full_xinjing_text}"
    )
    res = client.models.generate_content(
        model=TTS_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=TTS_VOICE
                    )
                )
            )
        )
    )
    cand = res.candidates[0]
    pcm = cand.content.parts[0].inline_data.data
    if isinstance(pcm, str):
        pcm = base64.b64decode(pcm)
    raw_wav_bytes = pcm_bytes_to_wav(pcm, sample_rate=TTS_SAMPLE_RATE)

    out_dir = os.path.join(PROJECT_ROOT, "public", "audio")
    raw_wav = os.path.join(out_dir, "xinjing_raw.wav")
    final_wav = os.path.join(out_dir, "xinjing_sanctuary.wav")
    final_mp3 = os.path.join(out_dir, "xinjing.mp3")

    with open(raw_wav, "wb") as f:
        f.write(raw_wav_bytes)

    apply_sanctuary_filter(raw_wav, final_wav)

    cmd = [
        "ffmpeg", "-y", "-i", final_wav.replace("\\", "/"),
        "-b:a", "192k",
        final_mp3.replace("\\", "/")
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    data, sr = sf.read(final_wav)
    total_dur = len(data) / sr

    with open(json_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    all_lines = []
    for p in json_data.get("paragraphs", []):
        for l in p.get("lines", []):
            all_lines.append(l)

    char_weights = []
    for l in all_lines:
        valid = [c for c in l.get("chars", []) if c.get("text", "").strip() and c.get("text") not in "，。！？；：、"]
        char_weights.append(max(1, len(valid)))

    start_offset = 0.3
    speech_dur = max(1.0, total_dur - start_offset - 0.7)
    total_chars = sum(char_weights)

    cur_t = start_offset
    for l, count in zip(all_lines, char_weights):
        l_dur = (count / total_chars) * speech_dur
        l_start = round(cur_t, 3)
        l_end = round(cur_t + l_dur, 3)
        l["lineStart"] = l_start
        l["lineEnd"] = l_end

        chars = l.get("chars", [])
        valid_chars = [c for c in chars if c.get("text", "").strip() and c.get("text") not in "，。！？；：、"]
        c_count = max(1, len(valid_chars))
        c_dur = (l_end - l_start) / c_count
        c_time = l_start
        for c in chars:
            if c.get("text", "").strip() and c.get("text") not in "，。！？；：、":
                c["startTime"] = round(c_time, 3)
                c["endTime"] = round(c_time + c_dur, 3)
                c_time += c_dur
        cur_t = l_end

    for idx, p in enumerate(json_data.get("paragraphs", [])):
        p["id"] = idx + 1
        p_lines = p.get("lines", [])
        if p_lines:
            p["startTime"] = p_lines[0]["lineStart"]
            p["endTime"] = p_lines[-1]["lineEnd"]
        else:
            p["startTime"] = 0.3
            p["endTime"] = round(total_dur, 3)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    if os.path.exists(raw_wav):
        os.remove(raw_wav)
    if os.path.exists(final_wav):
        os.remove(final_wav)

    print(f"\n🎉 《心经》全篇连续单次生成部署完毕！耗时: {time.time() - t0:.2f}s, 音长: {total_dur:.2f}s", flush=True)
    print(f"   MP3 路径: {final_mp3}")
    print(f"   时间轴已更新: {json_path}")

if __name__ == "__main__":
    main()
