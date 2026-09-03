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
    ("右膝着地", "右膝浊地"),     # zhuó
    ("愿乐欲闻", "愿要欲闻"),     # yào 四声
    ("降伏", "降服"),             # xiáng fú
    ("应云何", "英云何"),         # yīng, 阻断大模型自动纠错为“云何应”
    ("应如是", "英如是"),         # yīng
    ("应无所住", "英无所住"),     # yīng
    ("但应如所教住", "但英如所教住"), # yīng
    ("可思量不", "可思量否"),     # fǒu
    ("见如来不", "见如来否"),     # fǒu
    ("生实信不", "生实信否"),     # fǒu
    ("宁为多不", "宁为多否"),     # fǒu
    ("我相", "我向"),             # xiàng
    ("人相", "人向"),             # xiàng
    ("众生相", "众生向"),         # xiàng
    ("寿者相", "寿者向"),         # xiàng
    ("法相", "法向"),             # xiàng
    ("非法相", "非法向"),         # xiàng
    ("取相", "取向"),             # xiàng
    ("身相", "身向"),             # xiàng
    ("诸相", "诸向"),             # xiàng
    ("非相", "非向"),             # xiàng
    ("所有相", "所有向"),         # xiàng
    ("不住于相", "不住于向"),     # xiàng
    ("不住相", "不住向"),         # xiàng
    ("无住相", "无住向"),         # xiàng
    ("著我人", "浊我人"),         # zhuó
    ("不应取", "不英取"),         # yīng
    ("法尚应舍", "法尚英舍"),     # yīng
    ("不也", "否也"),             # fǒu yě 佛经古音正读
    ("四句偈", "四句记"),         # jì 四声
    ("为他人说", "位他人说"),     # wèi 四声
    ("其福胜彼", "其福圣彼"),     # shèng 四声
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

    import re
    for attempt in range(1, 6):
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
                print(f"   ⚠️ 尝试 {attempt} 返回空，等待 20s...", flush=True)
                time.sleep(20)
        except Exception as e:
            err_str = str(e)
            match = re.search(r"retry in (\d+\.?\d*)s", err_str) or re.search(r"retryDelay': '(\d+)s", err_str)
            wait_time = int(float(match.group(1))) + 5 if match else 65
            print(f"   ⚠️ 尝试 {attempt} 命中配额限制: 需等待 {wait_time}s 后重试...", flush=True)
            time.sleep(wait_time)
    return False

def align_json_to_audio_bursts(audio_path: str, json_path: str):
    print(f"📐 正在运行全局最优声学波形与行级动态规划对齐...", flush=True)
    data, sr = sf.read(audio_path)
    if data.ndim == 2:
        data = data.mean(axis=1)

    frame_len = int(sr * 0.02)
    hop_len = int(sr * 0.01)
    energy = np.array([np.sum(data[i:i+frame_len]**2) for i in range(0, len(data) - frame_len, hop_len)])
    times = np.arange(len(energy)) * 0.01

    energy_smooth = uniform_filter1d(energy, size=20)
    thresh = np.percentile(energy_smooth, 15)

    speech = energy_smooth > thresh
    raw_bursts = []
    in_burst = False
    b_start = 0

    for t, is_sp in zip(times, speech):
        if is_sp and not in_burst:
            in_burst = True
            b_start = t
        elif not is_sp and in_burst:
            in_burst = False
            if t - b_start >= 0.15:
                raw_bursts.append([round(b_start, 3), round(t, 3)])

    # 合并辅音闭塞与微小换气（< 0.28s），防止整句被碎切
    bursts = []
    for b in raw_bursts:
        if not bursts:
            bursts.append(b)
        else:
            if b[0] - bursts[-1][1] < 0.28:
                bursts[-1][1] = b[1]
            else:
                bursts.append(b)

    # 剔除 < 0.20s 的孤立杂音抖动
    bursts = [b for b in bursts if b[1] - b[0] >= 0.20]

    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    lines = []
    for p in doc.get("paragraphs", []):
        for l in p.get("lines", []):
            chars = [c for c in l.get("chars", []) if c.get("text", "").strip() and c.get("text") not in "，。！？；：、“”‘’『』《》〈〉"]
            if chars:
                lines.append((l, chars))

    N = len(lines)
    M = len(bursts)

    total_chars = sum(len(c) for _, c in lines)
    total_speech_time = sum(b[1] - b[0] for b in bursts)
    target_rate = total_speech_time / max(1, total_chars)

    if N >= M:
        # N 行聚类到 M 个独立连续爆发段，DP 划分
        dp = np.full((N + 1, M + 1), float('inf'))
        parent = np.zeros((N + 1, M + 1), dtype=int)
        dp[0][0] = 0.0

        for j in range(1, M + 1):
            b_dur = bursts[j-1][1] - bursts[j-1][0]
            for i in range(1, N + 1):
                k_chars = 0
                for k in range(i - 1, -1, -1):
                    k_chars += len(lines[k][1])
                    expected_dur = k_chars * target_rate
                    cost = (b_dur - expected_dur) ** 2
                    if dp[k][j-1] + cost < dp[i][j]:
                        dp[i][j] = dp[k][j-1] + cost
                        parent[i][j] = k

        curr_i = N
        line_groups = []
        for j in range(M, 0, -1):
            prev_i = parent[curr_i][j]
            line_groups.append(list(range(prev_i, curr_i)))
            curr_i = prev_i
        line_groups.reverse()

        for j, (b_st, b_et) in enumerate(bursts):
            grp = line_groups[j]
            grp_chars = [c for line_idx in grp for c in lines[line_idx][1]]
            if not grp_chars:
                continue

            b_dur = b_et - b_st
            char_dur = b_dur / len(grp_chars)
            c_time = b_st

            for line_idx in grp:
                line_obj, l_chars = lines[line_idx]
                for c in l_chars:
                    c["startTime"] = round(c_time, 3)
                    c["endTime"] = round(c_time + char_dur, 3)
                    c_time += char_dur
                line_obj["lineStart"] = l_chars[0]["startTime"]
                line_obj["lineEnd"] = l_chars[-1]["endTime"]
    else:
        # 极罕见情况：爆发段多于文本行，按字数比例在 burst 间分配
        c_idx = 0
        for b_idx, (b_st, b_et) in enumerate(bursts):
            b_time = b_et - b_st
            if b_idx == M - 1:
                chars_in_burst = total_chars - c_idx
            else:
                chars_in_burst = int(round(b_time / target_rate))
            chars_in_burst = min(chars_in_burst, total_chars - c_idx)

            all_valid_chars = [c for _, chars in lines for c in chars]
            assigned = all_valid_chars[c_idx : c_idx + chars_in_burst]
            if assigned:
                act_dur = b_time / len(assigned)
                c_t = b_st
                for c in assigned:
                    c["startTime"] = round(c_t, 3)
                    c["endTime"] = round(c_t + act_dur, 3)
                    c_t += act_dur
            c_idx += chars_in_burst

        for l_obj, l_chars in lines:
            valid_ts = [c for c in l_chars if "startTime" in c]
            if valid_ts:
                l_obj["lineStart"] = valid_ts[0]["startTime"]
                l_obj["lineEnd"] = valid_ts[-1]["endTime"]

    for p_idx, p in enumerate(doc.get("paragraphs", [])):
        p["id"] = p_idx + 1
        p_lines = [l for l in p.get("lines", []) if "lineStart" in l]
        if p_lines:
            p["startTime"] = p_lines[0]["lineStart"]
            p["endTime"] = p_lines[-1]["lineEnd"]

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    print(f"✅ 全局最优动态规划时间轴校准完成！总发声段: {M}, 经文行数: {N}, 音频时长: {len(data)/sr:.2f}s")

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
    ok_f = synthesize_voice(client, "Zephyr", fixed_text, female_mp3)
    time.sleep(20)

    # 2. 生成男声 (Charon)
    ok_m = synthesize_voice(client, "Charon", fixed_text, male_mp3)

    # 3. 部署默认 MP3
    if os.path.exists(female_mp3):
        with open(female_mp3, "rb") as f_in, open(default_mp3, "wb") as f_out:
            f_out.write(f_in.read())

    # 4. 1:1 声学物理爆发点对齐
    if ok_f or os.path.exists(female_mp3):
        align_json_to_audio_bursts(female_mp3, json_path)
        print(f"🎉 【{book_id} / {chapter_id}】全套母带与对齐就绪！\n")
    else:
        print(f"❌ 【{book_id} / {chapter_id}】合成失败，跳过对齐！\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python scripts/generate_chapter_master.py <book_id> <chapter_id>")
        print("示例: python scripts/generate_chapter_master.py jingangjing chapter_3")
        sys.exit(1)
    build_chapter(sys.argv[1], sys.argv[2])
