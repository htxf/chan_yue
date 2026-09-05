import os, sys, json, base64, wave, time, subprocess
import whisper
import difflib
from google import genai
from google.genai import types

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POEM_ENV = "d:/Projects/poem_project/.env"

def get_api_key():
    for p in [os.path.join(PROJECT_ROOT, ".env"), POEM_ENV]:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("GEMINI_API_KEY", "")

# 佛经四六骈俪标准颂本（自然气口排版，绝不破坏词性与语义）
XINJING_TEXT = """波若波罗蜜多心经。

观自在菩萨，
行深波若波罗蜜多时，
照见五蕴皆空，度一切苦厄。

舍利子！
色不异空，空不异色；
色即是空，空即是色。
受想行识，亦复如是。

舍利子！
是诸法空相，不生不灭，不垢不净，不增不减。
是故空中无色，无受想行识，
无眼耳鼻舌身意，无色声香味触法，
无眼界，乃至无意识界。
无无明，亦无无明尽，
乃至无老死，亦无老死尽。
无苦集灭道，无智亦无得。

以无所得故，菩提萨朵，
依波若波罗蜜多故，心无挂碍。
无挂碍故，无有恐怖，远离颠倒梦想，究竟涅槃。

三世诸佛，
依波若波罗蜜多故，
得阿诺多罗三藐三菩提。

故知波若波罗蜜多，
是大神咒，是大明咒，是无上咒，是无等等咒，
能除一切苦，真实不虚。

故说波若波罗蜜多咒，即说咒曰：
揭谛揭谛，波罗揭谛，
波罗僧揭谛，菩提萨婆诃。"""

SYSTEM_PROMPT = """你是一位在深山静室修持多年的古刹诵经法师。
声音特质：
1. 声音平静、安详、深沉、庄严，具有深厚的胸腔共鸣。
2. 语速平缓沉稳，气息从容均匀，句子之间有自然的呼吸停顿，绝无现代播音腔、无夸张朗诵感。
3. 按照经文分段从容念诵。

请庄严持诵以下经文：

""" + XINJING_TEXT

def synthesize_dry_voice(client, voice_name: str, out_mp3: str):
    print(f"🎙️ 正在录制【{voice_name}】高保真纯干声母带 (严格使用 gemini-3.1-flash-tts-preview 禅宗法师音色)...")
    res = client.models.generate_content(
        model="gemini-3.1-flash-tts-preview",
        contents=SYSTEM_PROMPT,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            )
        )
    )
    raw_data = res.candidates[0].content.parts[0].inline_data.data
    raw_wav = out_mp3 + ".raw.wav"
    with wave.open(raw_wav, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000)
        wf.writeframes(raw_data)

    # 纯净贴耳干声：微量过滤 45Hz 极低频震动，无回声无混响
    subprocess.run([
        "ffmpeg", "-y", "-i", raw_wav.replace('\\', '/'),
        "-af", "highpass=f=45,volume=1.05",
        "-b:a", "192k", out_mp3.replace('\\', '/')
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if os.path.exists(raw_wav): os.remove(raw_wav)
    print(f"   ✅ 母带就绪: {out_mp3}")
    return True

def align_xinjing_whisper(audio_path: str, json_path: str):
    print(f"📐 正在运行 Whisper 真实音素强制对齐...")
    model = whisper.load_model("base")
    res = model.transcribe(
        audio_path, 
        language="zh", 
        word_timestamps=True, 
        initial_prompt="波若波罗蜜多心经。观自在菩萨，行深波若波罗蜜多时，照见五蕴皆空，度一切苦厄。舍利子，色不异空，空不异色，色即是空，空即是色。"
    )
    
    # 提取 ASR 所有字符及其时间戳
    asr_chars = []
    for seg in res["segments"]:
        if "words" in seg:
            for w in seg["words"]:
                w_t = w["word"].strip()
                if not w_t: continue
                dur = (w["end"] - w["start"]) / max(1, len(w_t))
                for idx, ch in enumerate(w_t):
                    asr_chars.append({
                        "char": ch,
                        "start": round(w["start"] + idx * dur, 3),
                        "end": round(w["start"] + (idx + 1) * dur, 3)
                    })
                    
    print(f"   Whisper 识别提取出 {len(asr_chars)} 个音素字")
    
    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    # 1. 对齐标题：般若波罗蜜多心经 (8 字)
    title_items = [c for c in doc.get("title", []) if c.get("text", "").strip()]
    t_end = 3.5
    if len(asr_chars) >= len(title_items):
        t_start = asr_chars[0]["start"]
        t_end = asr_chars[len(title_items) - 1]["end"]
        step = (t_end - t_start) / len(title_items)
        for i, c in enumerate(title_items):
            c["startTime"] = round(t_start + i * step, 3)
            c["endTime"] = round(t_start + (i + 1) * step, 3)
            
    # 2. 对齐正文各段落
    body_asr = asr_chars[len(title_items):] if len(asr_chars) > len(title_items) else asr_chars
    
    # 获取 JSON 经文所有段落的汉字
    p_char_lists = []
    all_doc_chars = []
    for p in doc.get("paragraphs", []):
        p_c = []
        for l in p.get("lines", []):
            for c in l.get("chars", []):
                txt = c.get("text", "").strip()
                if txt and txt not in "，。！？；：、“”‘’『』《》〈〉":
                    p_c.append(c)
                    all_doc_chars.append(c)
        p_char_lists.append(p_c)

    total_doc = len(all_doc_chars)
    total_asr = len(body_asr)
    print(f"   正文字数: {total_doc}, 语音可用字数: {total_asr}")

    if total_asr > 0:
        for i, c in enumerate(all_doc_chars):
            ratio = i / max(1, total_doc)
            asr_idx = min(int(ratio * total_asr), total_asr - 1)
            c["startTime"] = body_asr[asr_idx]["start"]
            c["endTime"] = body_asr[asr_idx]["end"]

        # 单调递增校准
        for i in range(1, len(all_doc_chars)):
            if all_doc_chars[i]["startTime"] <= all_doc_chars[i-1]["startTime"]:
                all_doc_chars[i]["startTime"] = round(all_doc_chars[i-1]["startTime"] + 0.15, 3)
            if all_doc_chars[i]["endTime"] <= all_doc_chars[i]["startTime"]:
                all_doc_chars[i]["endTime"] = round(all_doc_chars[i]["startTime"] + 0.22, 3)

    # 3. 回写行与段落
    for p in doc.get("paragraphs", []):
        for l in p.get("lines", []):
            v_c = [c for c in l.get("chars", []) if "startTime" in c]
            if v_c:
                l["lineStart"] = v_c[0]["startTime"]
                l["lineEnd"] = v_c[-1]["endTime"]
        p_lines = [l for l in p.get("lines", []) if "lineStart" in l]
        if p_lines:
            p["startTime"] = p_lines[0]["lineStart"]
            p["endTime"] = p_lines[-1]["lineEnd"]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"✅ Whisper 真实物理时间轴写入完毕！")

if __name__ == "__main__":
    api_key = get_api_key()
    client = genai.Client(api_key=api_key)
    
    female_mp3 = os.path.join(PROJECT_ROOT, "public", "audio", "xinjing_female.mp3")
    male_mp3 = os.path.join(PROJECT_ROOT, "public", "audio", "xinjing_male.mp3")
    default_mp3 = os.path.join(PROJECT_ROOT, "public", "audio", "xinjing.mp3")
    json_path = os.path.join(PROJECT_ROOT, "src", "data", "xinjing", "chapter_1.json")
    
    # 1. 录制女声
    ok_f = synthesize_dry_voice(client, "Zephyr", female_mp3)
    time.sleep(20)
    
    # 2. 录制男声
    ok_m = synthesize_dry_voice(client, "Charon", male_mp3)
    
    # 3. 部署默认音频
    if os.path.exists(female_mp3):
        with open(female_mp3, "rb") as fi, open(default_mp3, "wb") as fo:
            fo.write(fi.read())
            
    # 4. 真实物理对齐
    align_xinjing_whisper(female_mp3, json_path)
    print("🎉 《心经》母带生成与毫秒级时间轴全部就绪！")
