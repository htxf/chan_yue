import os
import sys
import json
import time
import base64
import wave
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

# 统一锁定为 Aoede 温婉空灵女性音色
TTS_MODEL = "gemini-3.1-flash-tts-preview"
TTS_VOICE = "Aoede"
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
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if os.path.exists(tmp):
        if os.path.exists(out_wav_path):
            os.remove(out_wav_path)
        os.rename(tmp, out_wav_path)

def align_by_energy_pauses(audio_path, paragraphs):
    data, sr = sf.read(audio_path)
    total_dur = len(data) / sr

    flat_lines = []
    for p_idx, p in enumerate(paragraphs):
        for l_idx, l in enumerate(p.get("lines", [])):
            text = "".join(c.get("text", "") for c in l.get("chars", []))
            chars = [c for c in l.get("chars", []) if c.get("text", "").strip() and c.get("text") not in "，。！？；：、"]
            flat_lines.append({
                "p_idx": p_idx,
                "l_idx": l_idx,
                "line_ref": l,
                "text": text,
                "char_count": max(1, len(chars)),
                "is_sentence_end": text.endswith(("。", "！", "？", "；", "："))
            })

    weights = []
    for fl in flat_lines:
        w = fl["char_count"] * 1.0
        if fl["is_sentence_end"]:
            w += 1.8  # 句末深呼吸停顿
        else:
            w += 0.6  # 逗号轻停顿
        weights.append(w)

    total_w = sum(weights)
    lead_in = 0.35
    tail_out = 0.6
    effective_dur = max(1.0, total_dur - lead_in - tail_out)

    cur_time = lead_in
    for fl, w in zip(flat_lines, weights):
        l_dur = (w / total_w) * effective_dur
        l_start = round(cur_time, 3)
        l_end = round(cur_time + l_dur, 3)

        line = fl["line_ref"]
        line["lineStart"] = l_start
        line["lineEnd"] = l_end

        chars = line.get("chars", [])
        valid_chars = [c for c in chars if c.get("text", "").strip() and c.get("text") not in "，。！？；：、"]
        c_count = max(1, len(valid_chars))
        c_dur = l_dur / c_count
        c_time = l_start
        for c in chars:
            if c.get("text", "").strip() and c.get("text") not in "，。！？；：、":
                c["startTime"] = round(c_time, 3)
                c["endTime"] = round(c_time + c_dur, 3)
                c_time += c_dur

        cur_time = l_end

    for idx, p in enumerate(paragraphs):
        p["id"] = idx + 1
        p_lines = p.get("lines", [])
        if p_lines:
            p["startTime"] = p_lines[0]["lineStart"]
            p["endTime"] = p_lines[-1]["lineEnd"]
        else:
            p["startTime"] = 0.35
            p["endTime"] = round(total_dur, 3)

    return total_dur

def synthesize_track(client, title_name, text_for_tts, json_path, out_mp3_path):
    print(f"\n==================================================", flush=True)
    print(f"🌸 正在为【{title_name}】合成 Aoede 空灵女性原声...", flush=True)
    print(f"   字音已全面校准 (著衣->zhuó, 多故->duō 一声等)", flush=True)
    print(f"==================================================", flush=True)

    prompt = (
        "用温和清晰、典雅空灵的语气朗读以下古文经文：\n\n"
        f"{text_for_tts}"
    )

    t0 = time.time()
    raw_wav_bytes = None
    for attempt in range(1, 6):
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
            if cand.content and cand.content.parts:
                pcm = cand.content.parts[0].inline_data.data
                if isinstance(pcm, str):
                    pcm = base64.b64decode(pcm)
                raw_wav_bytes = pcm_bytes_to_wav(pcm, sample_rate=TTS_SAMPLE_RATE)
                break
            else:
                print(f"⚠️ 尝试 {attempt} 未返回数据 (FinishReason={cand.finish_reason})，等待 20s 重试...", flush=True)
                time.sleep(20)
        except Exception as e:
            print(f"⚠️ 尝试 {attempt} 发生异常: {e}，等待 30s 重试...", flush=True)
            time.sleep(30)

    if not raw_wav_bytes:
        print(f"❌ 【{title_name}】生成失败！", flush=True)
        return False

    raw_wav = out_mp3_path + ".raw.wav"
    final_wav = out_mp3_path + ".sanctuary.wav"

    with open(raw_wav, "wb") as f:
        f.write(raw_wav_bytes)

    apply_sanctuary_filter(raw_wav, final_wav)

    cmd = [
        "ffmpeg", "-y", "-i", final_wav.replace("\\", "/"),
        "-b:a", "192k",
        out_mp3_path.replace("\\", "/")
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    dur = align_by_energy_pauses(final_wav, data.get("paragraphs", []))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if os.path.exists(raw_wav):
        os.remove(raw_wav)
    if os.path.exists(final_wav):
        os.remove(final_wav)

    print(f"🎉 【{title_name}】Aoede 原声生成并部署成功！总时长: {dur:.2f}s, 耗时: {time.time() - t0:.2f}s", flush=True)
    print(f"   MP3 路径: {out_mp3_path}", flush=True)
    print(f"   时间轴已更新: {json_path}", flush=True)
    return True

def main():
    api_key = get_api_key()
    if not api_key:
        print("❌ 未找到 GEMINI_API_KEY！")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    # 1. 《心经》读音校正 (依波惹波罗蜜哆故 duō 一声)
    xinjing_text = (
        "观自在菩萨，行深波惹波罗蜜多时，照见五蕴皆空，度一切苦厄。"
        "赦利子，色不异空，空不异色，色即是空，空即是色，受想行识，亦复如是。"
        "赦利子，是诸法空向，不生不灭，不垢不净，不增不减。"
        "是故空中无色，无受想行识，无眼耳鼻舌身意，无色声香味触法，无眼界，乃至无意识界。"
        "无无明，亦无无明进，乃至无老死，亦无老死进。无苦集灭道，无智亦无得。"
        "以无所得故，菩提萨垛，依波惹波罗蜜哆故，心无挂碍；"
        "无挂碍故，无有恐怖，远离颠倒梦想，究竟涅盘。"
        "三世诸佛，依波惹波罗蜜哆故，得阿漏多罗三秒三菩提。"
        "故知波惹波罗蜜多，是大神咒，是大明咒，是无上咒，是无等等咒，能除一切苦，真实不虚。"
        "故说波惹波罗蜜多咒，即说咒曰：阶谛阶谛，波罗阶谛，波罗僧阶谛，菩提娑婆喝。"
    )

    # 2. 《金刚经》第一品读音校正 (浊衣持钵 zhuó 二声, 意时 yì 四声)
    jingang_ch1_text = (
        "如是我闻。意时，佛在赦卫国奇树几孤独园，与大比丘众千两百五十人俱。"
        "尔时，世尊食时，浊衣持钵，入赦卫大城乞食。"
        "于其城中，次第乞已，还至本处。"
        "饭食气，收衣钵，洗足已，敷座而坐。"
    )

    # 生成心经
    synthesize_track(
        client,
        "般若波罗蜜多心经",
        xinjing_text,
        os.path.join(PROJECT_ROOT, "src", "data", "xinjing", "chapter_1.json"),
        os.path.join(PROJECT_ROOT, "public", "audio", "xinjing.mp3")
    )

    print("\n⏳ 冷却等待 20s 后生成金刚经第一品...", flush=True)
    time.sleep(20)

    # 生成金刚经第一品
    synthesize_track(
        client,
        "金刚经 第一品 法会因由分",
        jingang_ch1_text,
        os.path.join(PROJECT_ROOT, "src", "data", "jingangjing", "chapter_1.json"),
        os.path.join(PROJECT_ROOT, "public", "audio", "jingangjing", "chapter_1.mp3")
    )

if __name__ == "__main__":
    main()
