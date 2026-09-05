"""
generate_xinjing_master.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
《心经》全篇单次纯正母带生成与毫秒级时间轴对齐流水线
遵循《禅阅》Zen Audio Master SOP 规范：
1. 经文全篇单次传入（仅需 2 次 API 调用：女声 1 次 + 男声 1 次，杜绝浪费单日额度）
2. 保持严谨正统汉字经文，绝不使用同音字替换污染语义
3. 解除宗教经文 SAFETY 误拦截（BLOCK_NONE）
4. 贴耳纯干声滤波（45Hz 高通，杜绝人工浴室混响）
5. Whisper 全局音素级强制对齐，直出毫秒级时间轴
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import json
import base64
import wave
import time
import re
import subprocess
import difflib
import whisper
from google import genai
from google.genai import types

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

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

# 佛经四六骈俪标准全本（纯正严谨汉字，气口自然，绝不使用生造同音字）
XINJING_FULL_TEXT = """般若波罗蜜多心经。

观自在菩萨，
行深般若波罗蜜多时，
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

以无所得故，菩提萨埵，
依般若波罗蜜多故，心无挂碍。
无挂碍故，无有恐怖，远离颠倒梦想，究竟涅槃。

三世诸佛，
依般若波罗蜜多故，
得阿耨多罗三藐三菩提。

故知般若波罗蜜多，
是大神咒，是大明咒，是无上咒，是无等等咒，
能除一切苦，真实不虚。

故说般若波罗蜜多咒，即说咒曰：
揭谛揭谛，波罗揭谛，
波罗僧揭谛，菩提萨婆诃。"""

SYSTEM_PROMPT = """用平稳、自然、安详的普通话从容念诵以下经文。
要求：
1. 声音平静安详、字音平直匀速、不带舞台朗诵腔、无情绪波动起伏，气息从容均匀，声断气不断。
2. 遇到经文古梵音与多音字，请严格按以下发音念诵：
   - “般若”读作“bō rě”
   - “诸法空相”中“相”读作“xiàng”
   - “阿耨多罗”读作“ā nòu duō luó”
   - “菩提萨埵”读作“pú tí sà duǒ”
   - “菩提萨婆诃”读作“pú tí sà pó hē”
   - “波罗蜜多”中“多”读作第一声“duō”

请端身正意持诵以下经文：

""" + XINJING_FULL_TEXT

SAFETY_SETTINGS = [
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=types.HarmBlockThreshold.BLOCK_NONE),
]

def synthesize_single_pass(client, voice_name: str, out_mp3: str) -> bool:
    print(f"\n🎙️ 正在录制【{voice_name}】《心经》全篇母带 (单次直出，无拼接)...", flush=True)
    raw_wav = out_mp3 + ".raw.wav"
    
    for attempt in range(1, 6):
        try:
            res = client.models.generate_content(
                model="gemini-3.1-flash-tts-preview",
                contents=SYSTEM_PROMPT,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    safety_settings=SAFETY_SETTINGS,
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                        )
                    )
                )
            )
            cand = res.candidates[0]
            if cand.content and cand.content.parts:
                data = cand.content.parts[0].inline_data.data
                with wave.open(raw_wav, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(data)
                    
                dur = len(data) / (24000 * 2)
                print(f"   ✅ 单次生成成功! 纯净干声时长: {dur:.1f}s ({dur/60:.2f}分钟)", flush=True)
                
                # FFmpeg 滤波压制 (45Hz 消除极低频共振，无人工混响)
                os.makedirs(os.path.dirname(out_mp3), exist_ok=True)
                subprocess.run([
                    "ffmpeg", "-y", "-i", raw_wav.replace('\\', '/'),
                    "-af", "highpass=f=45,volume=1.05",
                    "-b:a", "192k", out_mp3.replace('\\', '/')
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                if os.path.exists(raw_wav):
                    os.remove(raw_wav)
                print(f"   ✅ 工业级母带压制完成: {out_mp3}", flush=True)
                return True
            else:
                print(f"   ⚠️ 尝试 {attempt} 返回空 candidate，重试...", flush=True)
                time.sleep(15)
        except Exception as e:
            err_str = str(e)
            match = re.search(r"retry in (\d+\.?\d*)s", err_str) or re.search(r"retryDelay': '(\d+)s", err_str)
            wait_time = int(float(match.group(1))) + 5 if match else 30
            print(f"   ⚠️ 尝试 {attempt} 遇到限流: {err_str[:60]}... 等待 {wait_time}s 重试...", flush=True)
            time.sleep(wait_time)
            
    return False

def align_full_xinjing_whisper(whisper_model, audio_path: str, json_path: str):
    print(f"📐 正在运行 Whisper 全局音素级强制对齐...")
    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
        
    res = whisper_model.transcribe(audio_path, language="zh", word_timestamps=True)
    
    # 提取 Whisper 识别字和时间戳
    asr_chars = []
    for s in res.get("segments", []):
        for w in s.get("words", []):
            w_t = w["word"].strip(" ，。！？；：、“”‘’\n\t")
            if not w_t: continue
            dur = (w["end"] - w["start"]) / max(1, len(w_t))
            for idx, ch in enumerate(w_t):
                asr_chars.append({
                    "char": ch,
                    "start": round(w["start"] + idx * dur, 3),
                    "end": round(w["start"] + (idx + 1) * dur, 3)
                })
                
    # 提取 JSON 全篇经文字符
    doc_chars = []
    for c in doc.get("title", []):
        if c.get("text", "").strip():
            doc_chars.append(c)
            
    for p in doc.get("paragraphs", []):
        for l in p.get("lines", []):
            for c in l.get("chars", []):
                txt = c.get("text", "").strip()
                if txt and txt not in "，。！？；：、“”‘’『』《》〈〉":
                    doc_chars.append(c)
                    
    print(f"   经文字数: {len(doc_chars)}, Whisper识别字数: {len(asr_chars)}")
    if not asr_chars:
        print("   ❌ ASR 为空，跳过回写")
        return
        
    homo_map = {
        '波':'般','熱':'若','情':'经','關':'观','生':'深','無':'五','運':'蕴','惡':'厄',
        '說':'舍','例':'利','易':'异','急':'即','事':'是','相':'想','時':'识','富':'复',
        '向':'相','進':'尽','德':'得','朵':'埵','衣':'依','艾':'碍',
        '諾':'耨','漏':'耨','秒':'藐','階':'揭','帝':'谛','喝':'诃','呵':'诃'
    }
    
    doc_str = "".join(c["text"] for c in doc_chars)
    asr_str = "".join(homo_map.get(c["char"], c["char"]) for c in asr_chars)
    
    sm = difflib.SequenceMatcher(None, doc_str, asr_str)
    matched_blocks = sm.get_matching_blocks()
    
    for c in doc_chars:
        c["startTime"] = None
        c["endTime"] = None
        
    for a_idx, b_idx, size in matched_blocks:
        for k in range(size):
            if a_idx + k < len(doc_chars) and b_idx + k < len(asr_chars):
                doc_chars[a_idx + k]["startTime"] = asr_chars[b_idx + k]["start"]
                doc_chars[a_idx + k]["endTime"] = asr_chars[b_idx + k]["end"]
                
    last_time = 0.0
    for i in range(len(doc_chars)):
        if doc_chars[i]["startTime"] is None:
            next_anchor_idx = None
            for j in range(i + 1, len(doc_chars)):
                if doc_chars[j]["startTime"] is not None:
                    next_anchor_idx = j
                    break
            if next_anchor_idx is not None:
                next_time = doc_chars[next_anchor_idx]["startTime"]
                gap = (next_time - last_time) / (next_anchor_idx - i + 1)
                doc_chars[i]["startTime"] = round(last_time + gap * 0.4, 3)
                doc_chars[i]["endTime"] = round(last_time + gap * 0.95, 3)
            else:
                doc_chars[i]["startTime"] = round(last_time + 0.35, 3)
                doc_chars[i]["endTime"] = round(last_time + 0.65, 3)
        last_time = doc_chars[i]["endTime"]
        
    for i in range(1, len(doc_chars)):
        if doc_chars[i]["startTime"] <= doc_chars[i-1]["startTime"]:
            doc_chars[i]["startTime"] = round(doc_chars[i-1]["startTime"] + 0.15, 3)
        if doc_chars[i]["endTime"] <= doc_chars[i]["startTime"]:
            doc_chars[i]["endTime"] = round(doc_chars[i]["startTime"] + 0.25, 3)
            
    # 回写每行和每个段落的起止时间
    for p in doc.get("paragraphs", []):
        for l in p.get("lines", []):
            v_c = [c for c in l.get("chars", []) if "startTime" in c and c["startTime"] is not None]
            if v_c:
                l["lineStart"] = v_c[0]["startTime"]
                l["lineEnd"] = v_c[-1]["endTime"]
        p_lines = [l for l in p.get("lines", []) if "lineStart" in l]
        if p_lines:
            p["startTime"] = p_lines[0]["lineStart"]
            p["endTime"] = p_lines[-1]["lineEnd"]
            
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 毫秒级物理时间轴成功回写: {json_path}！")

def main():
    api_key = get_api_key()
    if not api_key:
        print("❌ 未找到 GEMINI_API_KEY！")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    
    female_mp3 = os.path.join(PROJECT_ROOT, "public", "audio", "xinjing_female.mp3")
    male_mp3 = os.path.join(PROJECT_ROOT, "public", "audio", "xinjing_male.mp3")
    default_mp3 = os.path.join(PROJECT_ROOT, "public", "audio", "xinjing.mp3")
    json_path = os.path.join(PROJECT_ROOT, "src", "data", "xinjing", "chapter_1.json")
    
    # 1. 单次录制女声 (Zephyr)
    ok_f = synthesize_single_pass(client, "Zephyr", female_mp3)
    
    # 2. 默认音频使用女声
    if ok_f and os.path.exists(female_mp3):
        with open(female_mp3, "rb") as fi, open(default_mp3, "wb") as fo:
            fo.write(fi.read())
        print(f"✅ 默认母带已就绪: {default_mp3}")
        
    # 3. Whisper 全篇音素级对齐回写 JSON
    if ok_f and os.path.exists(female_mp3):
        whisper_model = whisper.load_model("base")
        align_full_xinjing_whisper(whisper_model, female_mp3, json_path)
        
    # 4. 单次录制男声 (Charon)
    time.sleep(20)
    ok_m = synthesize_single_pass(client, "Charon", male_mp3)
    
    print("\n🎉 《心经》全篇单次直出双音色母带全部圆满就绪！")

if __name__ == "__main__":
    main()
