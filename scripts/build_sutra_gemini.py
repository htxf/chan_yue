"""
build_sutra_gemini.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
《禅悦》经文高保真诵读生成引擎（Google Gemini 3.1 Flash TTS 版）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【标准声学配置】
1. TTS 引擎: Google Gemini 3.1 Flash TTS (gemini-3.1-flash-tts-preview)
2. 音色: Fenrir (沉稳、自然、字音精准的男声)
3. 风格提示词: 沉着平和、从容舒缓的标准普通话朗诵
4. 声学滤镜: 古刹幽鸣 · 加强版 (1.5x 空灵空间残响 + 150Hz 温暖殿堂低频)
5. 自动对齐: 毫秒级行级与字级时间戳自动计算并写入 JSON 数据
6. 频控保护: 每次请求间隔 15s，防止超出 API 配额

【用法】
- 单品生成测试: python scripts/build_sutra_gemini.py 1
- 指定多品生成: python scripts/build_sutra_gemini.py 2 3 4
- 全本批量生成: python scripts/build_sutra_gemini.py all
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
POEM_ENV = "d:/Projects/poem_project/.env"

def get_api_key():
    # 优先从本项目的 .env，其次从 poem_project/.env，最后从环境变量
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
RATE_LIMIT_DELAY = 15  # 秒，配额保护间隔

# 古刹幽鸣 · 加强版（1.5x 空灵空间感）声学滤镜
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
    """应用古刹幽鸣 1.5x 声学空间滤镜"""
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

from buddhist_dict import clean_tts_text

def extract_chapter_text(chapter_data: dict) -> str:
    """从章节 JSON 中提取完整诵读文本"""
    lines_text = []
    for p in chapter_data.get("paragraphs", []):
        for line in p.get("lines", []):
            line_str = "".join(c.get("text", "") for c in line.get("chars", []))
            lines_text.append(line_str)
    return "\n".join(lines_text)

def update_chapter_timestamps(json_path: str, audio_path: str):
    """根据生成的实际音频时长，精准计算各段各行各字的时间戳"""
    data, sr = sf.read(audio_path)
    total_dur = len(data) / sr

    with open(json_path, "r", encoding="utf-8") as f:
        chapter_data = json.load(f)

    # 统计所有有效字符
    all_lines = []
    for p in chapter_data.get("paragraphs", []):
        for l in p.get("lines", []):
            all_lines.append(l)

    char_weights = []
    for l in all_lines:
        valid = [c for c in l.get("chars", []) if c.get("text", "").strip() and c.get("text") not in "，。！？；：、"]
        char_weights.append(max(1, len(valid)))

    start_offset = 0.25
    speech_dur = max(1.0, total_dur - start_offset - 0.6)
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

    # 更新段落级时间
    p_cur = 0.25
    for p in chapter_data.get("paragraphs", []):
        p_lines = p.get("lines", [])
        if p_lines:
            p["startTime"] = p_lines[0]["lineStart"]
            p["endTime"] = p_lines[-1]["lineEnd"]
        else:
            p["startTime"] = 0.25
            p["endTime"] = round(total_dur, 3)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(chapter_data, f, ensure_ascii=False, indent=2)

    return total_dur

def build_chapter(client, chapter_num: int):
    """合成单个章节音频并部署"""
    json_path = os.path.join(PROJECT_ROOT, "src", "data", "jingangjing", f"chapter_{chapter_num}.json")
    if not os.path.exists(json_path):
        print(f"❌ 找不到经文数据: {json_path}")
        return False

    with open(json_path, "r", encoding="utf-8") as f:
        chapter_data = json.load(f)

    raw_sutra_text = extract_chapter_text(chapter_data)
    # 应用佛教发音精准校对字典
    sutra_text = clean_tts_text(raw_sutra_text)
    
    prompt = (
        "请用沉着、平和、清晰、从容的标准普通话朗读以下经文，"
        "语调自然平稳，字音准确，不急不缓，字字分明：\n\n"
        f"{sutra_text}"
    )

    print(f"\n==================================================", flush=True)
    print(f"📖 正在生成《金刚经》第 {chapter_num} 品...", flush=True)
    print(f"   经文字数: {len(raw_sutra_text)} 字", flush=True)

    t0 = time.time()
    try:
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
        if not cand.content or not cand.content.parts:
            print(f"⚠️ 生成未返回数据 (FinishReason={cand.finish_reason})")
            return False

        pcm = cand.content.parts[0].inline_data.data
        if isinstance(pcm, str):
            pcm = base64.b64decode(pcm)
        raw_wav_bytes = pcm_bytes_to_wav(pcm, sample_rate=TTS_SAMPLE_RATE)

    except Exception as e:
        print(f"❌ Gemini 请求失败: {e}")
        return False

    # 导出并处理音频
    audio_dir = os.path.join(PROJECT_ROOT, "public", "audio", "jingangjing")
    os.makedirs(audio_dir, exist_ok=True)
    raw_wav = os.path.join(audio_dir, f"chapter_{chapter_num}_raw.wav")
    final_wav = os.path.join(audio_dir, f"chapter_{chapter_num}_sanctuary.wav")
    final_mp3 = os.path.join(audio_dir, f"chapter_{chapter_num}.mp3")

    with open(raw_wav, "wb") as f:
        f.write(raw_wav_bytes)

    apply_sanctuary_filter(raw_wav, final_wav)

    # 编码 192k MP3
    cmd = [
        "ffmpeg", "-y", "-i", final_wav.replace("\\", "/"),
        "-b:a", "192k",
        final_mp3.replace("\\", "/")
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 更新时间戳
    dur = update_chapter_timestamps(json_path, final_wav)

    # 清理中间 wav
    if os.path.exists(raw_wav):
        os.remove(raw_wav)
    if os.path.exists(final_wav):
        os.remove(final_wav)

    print(f"✅ 第 {chapter_num} 品生成完成！耗时: {time.time() - t0:.2f}s, 音频时长: {dur:.2f}s", flush=True)
    print(f"   MP3 文件: {final_mp3}", flush=True)
    print(f"   时间轴已更新: {json_path}", flush=True)
    return True

def main():
    api_key = get_api_key()
    if not api_key:
        print("❌ 未找到 GEMINI_API_KEY！请在 .env 文件中设置。")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    args = sys.argv[1:]
    if not args:
        print("用法:")
        print("  python scripts/build_sutra_gemini.py 1       # 生成第1品")
        print("  python scripts/build_sutra_gemini.py 2 3 4   # 生成第2,3,4品")
        print("  python scripts/build_sutra_gemini.py all     # 批量生成1~32品")
        sys.exit(0)

    if args[0].lower() == "all":
        chapter_nums = list(range(1, 33))
    else:
        chapter_nums = [int(a) for a in args if a.isdigit()]

    print(f"🚀 即将处理 {len(chapter_nums)} 个章节: {chapter_nums}")
    for idx, c_num in enumerate(chapter_nums):
        build_chapter(client, c_num)
        if idx < len(chapter_nums) - 1:
            print(f"⏳ 触发配额保护，等待 {RATE_LIMIT_DELAY}s 后处理下一品...", flush=True)
            time.sleep(RATE_LIMIT_DELAY)

if __name__ == "__main__":
    main()
