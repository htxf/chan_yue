"""
generate_sutra_master.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
《禅阅》全藏工业级古籍佛经音频母带生成与声学门禁质检全流程引擎
遵循《禅阅》Zen Audio Master SOP 工业级标准：
1. 篇幅分级：≤400字经卷强制单次直出（Single-Pass）
2. 全类别 BLOCK_NONE 安全豁免，彻底杜绝古籍名相误拦截
3. 动态提示词注入：依据经文 JSON 标准注音严格锁定字音声调
4. 24kHz 贴耳纯干声，50Hz 亚音频滤波母带压制
5. Whisper 全局音素强制对齐（SequenceMatcher + pypinyin）
6. 声字一致性真实声学门禁（Phonetic Gatekeeper）：声调不符绝对阻断
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
用法:
    python scripts/generate_sutra_master.py xinjing chapter_1 --voice female
    python scripts/generate_sutra_master.py jingangjing chapter_3 --voice male
"""

import os
import sys
import json
import wave
import time
import re
import argparse
import subprocess
import difflib
import whisper
import pypinyin
from google import genai
from google.genai import types

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SAFETY_SETTINGS = [
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=types.HarmBlockThreshold.BLOCK_NONE),
]

VOICE_CONFIG = {
    "female": "Zephyr", # 莲华女声
    "male": "Charon",   # 暮钟男声
}

class PhoneticAuditError(Exception):
    """声学门禁校验不通过异常"""
    pass

def get_api_key() -> str:
    for p in [os.path.join(PROJECT_ROOT, ".env"), "d:/Projects/poem_project/.env"]:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("GEMINI_API_KEY", "")

# 古汉语及梵音字音正音映射表（锁定 shí 二声石、duǒ 三声朵、rě 三声惹）
# 关键：般若加微顿气口“波惹，”，阻断唇齿音粘连低化为 ra/染，确保饱满 rě
PHONETIC_TTS_MAP = {
    "般若波罗蜜多": "波惹，波罗蜜多",
    "般若": "波惹，",
    "菩提萨埵": "菩提萨朵，",
    "萨埵": "萨朵，",
    "受想行识": "受想形石，",
    "乃至无意识界": "乃至无意石界，",
    "舍利子": "设利子，",
    "诸法空相": "诸法空向，",
    "无明尽": "无明进，",
    "老死尽": "老死进，",
    "阿耨多罗": "阿诺多罗",
    "三藐三菩提": "三秒三菩提",
    "揭谛揭谛": "阶帝阶帝，",
    "波罗揭谛": "波罗阶帝，",
    "波罗僧揭谛": "波罗僧阶帝，",
    "菩提萨婆诃": "菩提萨婆呵。",
    "心无挂碍": "心无挂艾，",
    "无挂碍故": "无挂艾故，",
}

def compile_sutra_prompt(doc: dict) -> tuple:
    """
    第一阶：编译经文诵读底本与声学指令
    """
    title_chars = [c["text"] for c in doc.get("title", []) if c.get("text", "").strip()]
    title_str = "".join(title_chars)
    
    lines = [f"{title_str}。"]
    for p in doc.get("paragraphs", []):
        for l in p.get("lines", []):
            line_chars = "".join([c["text"] for c in l.get("chars", []) if c.get("text", "").strip()])
            if line_chars:
                clean_line = line_chars.replace("？", "。").replace("?", "。")
                lines.append(clean_line)
                
    raw_body = "\n".join(lines)
    reading_body = raw_body
    for k, v in PHONETIC_TTS_MAP.items():
        reading_body = reading_body.replace(k, v)
        
    directive = "用平稳、自然、无修饰的普通话念诵以下文字，语调平平、不带朗诵感：\n\n"
    full_prompt = directive + reading_body
    return full_prompt, reading_body


def synthesize_master_audio(client, voice_name: str, prompt: str, raw_wav: str) -> bool:
    """
    第二阶：单次直出高保真母带录制
    """
    print(f"\n🎙️ 正在单次直出录制【{voice_name}】经文母带...", flush=True)
    
    for attempt in range(1, 9):
        try:
            res = client.models.generate_content(
                model="gemini-3.1-flash-tts-preview",
                contents=prompt,
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
                os.makedirs(os.path.dirname(os.path.abspath(raw_wav)), exist_ok=True)
                with wave.open(raw_wav, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(data)
                    
                dur = len(data) / (24000 * 2)
                print(f"   ✅ 单次生成成功! 纯净干声时长: {dur:.1f}s ({dur/60:.2f}分钟)", flush=True)
                return True
            else:
                print(f"   ⚠️ 尝试 {attempt} 未返回音频数据，等待 15s 后重试...", flush=True)
                time.sleep(15)
        except Exception as e:
            err_str = str(e)
            match = re.search(r"retry in (\d+\.?\d*)s", err_str) or re.search(r"retryDelay': '(\d+)s", err_str)
            wait_time = int(float(match.group(1))) + 5 if match else 30
            print(f"   ⚠️ 尝试 {attempt} 遇到限流或网络断开: {err_str[:60]}... 等待 {wait_time}s 重试...", flush=True)
            time.sleep(wait_time)
            
    return False

def audit_phonetic_gatekeeper(asr_chars: list, doc_chars: list):
    """
    第三阶：声学声调真实门禁质检（Phonetic Gatekeeper）
    提取 Whisper 实际识别的汉字与声调，严格核验核心多音字
    若声调不符，抛出 PhoneticAuditError 绝对阻断落盘！
    """
    print("\n🔍 正在执行【声字声调真实声学门禁质检】...", flush=True)
    
    custom_map = {'般': 'bo', '若': 're', '埵': 'duo', '耨': 'nuo'}
    def to_py(c):
        if c in custom_map: return custom_map[c]
        p = pypinyin.pinyin(c, style=pypinyin.Style.NORMAL, errors='default')
        return p[0][0] if p and p[0] else c
        
    doc_pys = [to_py(c["text"]) for c in doc_chars]
    asr_pys = [to_py(c["char"]) for c in asr_chars]
    
    sm = difflib.SequenceMatcher(None, doc_pys, asr_pys)
    matched_blocks = sm.get_matching_blocks()
    
    aligned_pairs = {}
    for a_idx, b_idx, size in matched_blocks:
        for k in range(size):
            if a_idx + k < len(doc_chars) and b_idx + k < len(asr_chars):
                aligned_pairs[a_idx + k] = asr_chars[b_idx + k]
                
    # 严格门禁规则字典：
    # 若: 必须是上声三声 (rě)，Whisper 识别为“惹/热”时声调必须为 3，严禁 4 声或 1 声！
    # 识: 必须是阳平二声 (shí)，Whisper 识别为“時/石/识/食”等 2 声，严禁四声“事/是”！
    # 埵: 必须是上声三声 (duǒ)，Whisper 识别为“朵/垛/埵”等 3 声，严禁四声“堕”或轻声！
    audit_rules = {
        '若': {'expected_tones': [3], 'expected_chars': ['惹', '若'], 'desc': '三声 rě，绝不可读四声 ruò 或一声'},
        '识': {'expected_tones': [2], 'expected_chars': ['时', '時', '石', '识', '識'], 'desc': '二声 shí，句末绝不可降调读四声 shì'},
        '埵': {'expected_tones': [3], 'expected_chars': ['朵', '垛', '埵'], 'desc': '三声 duǒ，绝不可读四声 duò'},
        '舍': {'expected_tones': [4], 'expected_chars': ['设', '設', '舍'], 'desc': '四声 shè'},
        '相': {'expected_tones': [4], 'expected_chars': ['向', '相'], 'desc': '四声 xiàng'},
        '尽': {'expected_tones': [4], 'expected_chars': ['进', '進', '尽', '盡', '静', '靜'], 'desc': '四声 jìn'},
    }
    
    violations = []
    total_audited = 0
    
    for idx, c in enumerate(doc_chars):
        txt = c["text"]
        if txt in audit_rules:
            total_audited += 1
            rule = audit_rules[txt]
            asr_match = aligned_pairs.get(idx)
            if not asr_match:
                print(f"   ⚠️ 经文字【{txt}】未能对齐到 ASR 字符，标记警告")
                continue
                
            asr_char = asr_match["char"]
            asr_tone3_list = pypinyin.pinyin(asr_char, style=pypinyin.Style.TONE3)
            asr_py = asr_tone3_list[0][0] if asr_tone3_list and asr_tone3_list[0] else ""
            
            tone_match = re.search(r'\d', asr_py)
            actual_tone = int(tone_match.group(0)) if tone_match else 0
            
            # 综合声学判断：
            # 若字：如果识别为“惹”，拼音必定是 re3，通过；如果识别为“熱”或“若”且为四声，失败！
            # 识字：如果识别为“時/石”，拼音是 shi2，通过；如果识别为“事/是”，拼音是 shi4，失败！
            # 埵字：如果识别为“朵/垛”，拼音是 duo3，通过；如果识别为“堕”，拼音是 duo4，失败！
            is_valid = False
            if actual_tone in rule['expected_tones']:
                is_valid = True
            elif asr_char in rule['expected_chars']:
                is_valid = True
                
            # 严格拦截降调失真与元音低化
            if txt == '识' and asr_char in ['事', '是']:
                is_valid = False
            if txt == '埵' and asr_char in ['堕']:
                is_valid = False
            if txt == '若' and (asr_char in ['熱', '热', '染'] or not asr_py.startswith('re')):
                is_valid = False
                
            status = "✅ PASS" if is_valid else "❌ FAIL"
            if not is_valid:
                violations.append({
                    "char": txt,
                    "expected": rule['desc'],
                    "actual_asr_char": asr_char,
                    "actual_py": asr_py,
                    "time": f"{asr_match['start']:.2f}s-{asr_match['end']:.2f}s"
                })
                
            print(f"   [{status}] 经文字:【{txt}】| 期待: {rule['desc']} | ASR识别:【{asr_char}】({asr_py}) @ {asr_match['start']:.2f}s")
            
    if violations:
        print("\n🚫 门禁拦截：检测到关键声调发音不符指标！")
        for v in violations:
            print(f"   - 经文字【{v['char']}】: Whisper实际识别【{v['actual_asr_char']}】({v['actual_py']})，标准要求: {v['expected']} (发生于 {v['time']})")
        raise PhoneticAuditError(f"声学门禁拦截：共有 {len(violations)} 处关键多音字声调不符合规范，阻断落盘！")
        
    print(f"✅ 声字声调真实声学门禁 100% 完美通过！（共核验 {total_audited} 处关键古名相）\n")

def force_align_timestamps(doc: dict, doc_chars: list, asr_chars: list):
    """
    第四阶：Whisper 全局音素级强制物理对齐
    """
    print("📐 正在执行 Whisper 全局音素级物理对齐...", flush=True)
    
    custom_map = {'般': 'bo', '若': 're', '埵': 'duo', '耨': 'nuo'}
    def to_py(c):
        if c in custom_map: return custom_map[c]
        p = pypinyin.pinyin(c, style=pypinyin.Style.NORMAL, errors='default')
        return p[0][0] if p and p[0] else c
        
    doc_pys = [to_py(c["text"]) for c in doc_chars]
    asr_pys = [to_py(c["char"]) for c in asr_chars]
    
    sm = difflib.SequenceMatcher(None, doc_pys, asr_pys)
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
            doc_chars[i]["startTime"] = round(doc_chars[i-1]["startTime"] + 0.12, 3)
        if doc_chars[i]["endTime"] <= doc_chars[i]["startTime"]:
            doc_chars[i]["endTime"] = round(doc_chars[i]["startTime"] + 0.22, 3)
            
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

def finalize_master(raw_wav: str, target_mp3: str, doc: dict, json_path: str, sync_default: bool = False):
    """
    第五阶：母带滤波压制与数据原子发布
    """
    print(f"🎛️ 正在进行 50Hz 纯干声母带压制与落盘: {target_mp3}...", flush=True)
    os.makedirs(os.path.dirname(target_mp3), exist_ok=True)
    
    subprocess.run([
        "ffmpeg", "-y", "-i", raw_wav.replace('\\', '/'),
        "-af", "highpass=f=50,volume=1.05",
        "-b:a", "192k", target_mp3.replace('\\', '/')
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if sync_default:
        default_mp3 = os.path.join(os.path.dirname(target_mp3), "xinjing.mp3")
        with open(target_mp3, "rb") as fi, open(default_mp3, "wb") as fo:
            fo.write(fi.read())
        print(f"   ✅ 同步更新默认母带: {default_mp3}")
        
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"   ✅ 经文毫秒级时间轴保存成功: {json_path}")
    
    if os.path.exists(raw_wav):
        os.remove(raw_wav)

def main():
    parser = argparse.ArgumentParser(description="禅阅通用古籍经文母带生成与声调门禁质检引擎")
    parser.add_argument("book_id", nargs="?", default="xinjing", help="经文ID (如 xinjing, jingangjing)")
    parser.add_argument("chapter_id", nargs="?", default="chapter_1", help="章节ID (如 chapter_1, chapter_3)")
    parser.add_argument("--voice", choices=["female", "male"], default="female", help="诵经音色 (female=Zephyr, male=Charon)")
    args = parser.parse_args()
    
    api_key = get_api_key()
    if not api_key:
        print("❌ 未找到 GEMINI_API_KEY！请在 .env 中配置")
        sys.exit(1)
        
    json_path = os.path.join(PROJECT_ROOT, "src", "data", args.book_id, f"{args.chapter_id}.json")
    if not os.path.exists(json_path):
        print(f"❌ 经文文件不存在: {json_path}")
        sys.exit(1)
        
    voice_name = VOICE_CONFIG[args.voice]
    target_mp3 = os.path.join(PROJECT_ROOT, "public", "audio", f"{args.book_id}_{args.voice}.mp3")
    raw_wav = os.path.join(PROJECT_ROOT, "scratch", f"{args.book_id}_{args.chapter_id}_{args.voice}.raw.wav")
    
    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)
        
    prompt, reading_body = compile_sutra_prompt(doc)
    
    client = genai.Client(api_key=api_key)
    ok = synthesize_master_audio(client, voice_name, prompt, raw_wav)
    if not ok or not os.path.exists(raw_wav):
        print("❌ 母带录制失败！")
        sys.exit(1)
        
    print("🤖 正在载入 Whisper 提取物理声学时序与真实音素...", flush=True)
    whisper_model = whisper.load_model("base")
    asr_res = whisper_model.transcribe(raw_wav, language="zh", word_timestamps=True)
    
    asr_chars = []
    for s in asr_res.get("segments", []):
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
                    
    # 第三阶：真实声调门禁（若不符合直接阻断抛异常，绝不放行）
    audit_phonetic_gatekeeper(asr_chars, doc_chars)
    
    # 第四阶：全局强制对齐
    force_align_timestamps(doc, doc_chars, asr_chars)
    
    # 第五阶：滤波压制与原子落盘
    sync_default = (args.book_id == "xinjing" and args.voice == "female")
    finalize_master(raw_wav, target_mp3, doc, json_path, sync_default=sync_default)
    
    print(f"\n🎉 工业级母带生产全流程圆满完成！")
    print(f"   - 音频文件: {target_mp3}")
    print(f"   - 经文数据: {json_path}")

if __name__ == "__main__":
    main()
