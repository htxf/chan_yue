import os
import sys
import json
import time
import subprocess
import soundfile as sf
import numpy as np
import torch
import torchaudio

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_REF_DIR = os.path.join(PROJECT_ROOT, "audio_ref")
SAMPLE_WAV = os.path.join(PROJECT_ROOT, "sample.wav")

# 严密审校的《心经》逐句发音校准表
PARAGRAPH_TTS_MAP = {
    1: "观自在菩萨，",
    2: "形深播惹波罗蜜多时，",                   # 般若 -> 播惹，形深
    3: "照见五蕴皆空，",                         # 独立句，绝不与下句粘连
    4: "度一切苦厄。",                           # 独立句
    5: "赦利子，色不异空，空不异色，",           # 舍利 -> 赦利
    6: "色即是空，空即是色，",
    7: "受想形识，亦复如是。",                   # 行识 -> 形识
    8: "赦利子，是诸法空向，",                   # 空相 -> 空向（确保四声 xiàng！）
    9: "不生不灭，不垢不净，不增不减。",
    10: "是故空中无色，无受想形识，",            # 行识 -> 形识
    11: "无眼耳鼻舌身意，无色声香味触法，",
    12: "无眼界，乃至无意识界。",
    13: "无无明，亦无无明进，",                 # 尽 -> 进（确保前鼻音四声 jìn！）
    14: "乃至无老死，亦无老死进。",             # 尽 -> 进（确保前鼻音四声 jìn！）
    15: "无苦集灭道，无智亦无德。",             # 得 -> 德（dé）
    16: "以无所得故，菩提萨朵，",               # 萨埵 -> 萨朵
    17: "衣播惹波罗蜜多故，心无挂碍，",         # 依 -> 衣（确保一声 yī！），波罗蜜多连贯不被切断
    18: "无挂碍故，无有恐怖，远离颠倒梦想，",
    19: "究竟涅盘。",                           # 涅槃 -> 涅盘
    20: "三世诸佛，衣播惹波罗蜜多故，",         # 依 -> 衣（一声 yī！）
    21: "德，锕耨多罗三秒三菩提。",             # 得阿 -> 德，锕（微顿 + 第一声 ā）
    22: "故知播惹波罗蜜多，是大神咒，是大明咒，", # 般若 -> 播惹
    23: "是无上咒，是无等等咒，",
    24: "能除一切苦，真实不虚。",
    25: "故说播惹波罗蜜多咒，",                 # 般若 -> 播惹
    26: "即说咒曰：",
    27: "阶谛阶谛，波罗阶谛，波罗僧阶谛，菩提萨婆喝。" # 揭谛 -> 阶谛，萨婆诃 -> 萨婆喝
}

def custom_load(filepath, **kwargs):
    data, sr = sf.read(filepath, dtype='float32')
    tensor = torch.from_numpy(data)
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    else:
        tensor = tensor.t()
    return tensor, sr

torchaudio.load = custom_load

def init_model():
    from f5_tts.infer.utils_infer import load_vocoder, load_model
    from huggingface_hub import hf_hub_download
    from f5_tts.model import DiT
    
    print("⚙️ 加载 F5-TTS 声纹克隆引擎...", flush=True)
    ckpt_path = hf_hub_download(repo_id='SWivid/F5-TTS', filename='F5TTS_v1_Base/model_1250000.safetensors', local_files_only=True)
    vocoder = load_vocoder()
    model_cfg = dict(dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512, conv_layers=4)
    ema_model = load_model(DiT, model_cfg, ckpt_path)
    print("✅ 模型加载成功！", flush=True)
    return ema_model, vocoder

def trim_silence(wave, sr, threshold=0.015):
    abs_wave = np.abs(wave)
    non_silent = np.where(abs_wave > threshold)[0]
    if len(non_silent) > 0:
        start_idx = max(0, non_silent[0] - int(0.02 * sr))
        end_idx = min(len(wave), non_silent[-1] + int(0.04 * sr))
        return wave[start_idx:end_idx]
    return wave

def main():
    json_path = os.path.join(PROJECT_ROOT, "src", "data", "xinjing", "chapter_1.json")
    with open(json_path, "r", encoding="utf-8") as f:
        chapter_data = json.load(f)

    # 提取参考音频
    ref_wav = os.path.join(AUDIO_REF_DIR, "ref_clean_6s.wav")
    ref_text = "善男子、善女人，发阿耨多罗三藐三菩提心，应如是住。"
    
    data, sr = sf.read(SAMPLE_WAV)
    if data.ndim == 2:
        data = data.mean(axis=1)
    start_idx = int(54.8 * sr)
    end_idx = int(63.2 * sr)
    sf.write(ref_wav, data[start_idx:end_idx], sr)

    ema_model, vocoder = init_model()
    from f5_tts.infer.utils_infer import infer_process, preprocess_ref_audio_text

    ref_audio, r_text = preprocess_ref_audio_text(ref_wav, ref_text)
    sr_target = 24000

    print("\n==================================================", flush=True)
    print("🚀 逐句独立生成《心经》27 个段落（杜绝任何内部断词与切断）", flush=True)
    print("==================================================", flush=True)

    para_records = []
    
    # 段落间大停顿的 ID（段落转换处停顿 0.55s，句内停顿 0.35s）
    MAJOR_SECTION_ENDS = {4, 7, 9, 12, 15, 19, 21, 24, 26}

    for p in chapter_data["paragraphs"]:
        p_id = p["id"]
        # 获取原文
        raw_chars = [c.get("text", "") for l in p.get("lines", []) for c in l.get("chars", [])]
        raw_text = "".join(raw_chars).strip()
        
        tts_text = PARAGRAPH_TTS_MAP.get(p_id, raw_text)
        
        print(f"\n▶ [{p_id}/27] 段落 {p_id}:", flush=True)
        print(f"   原文: {raw_text}", flush=True)
        print(f"   发音: {tts_text}", flush=True)

        t0 = time.time()
        # 确保单句以标点结尾
        tts_input = tts_text
        if not tts_input.endswith(('，', '。', '！', '？', '；', '：')):
            tts_input += '。'

        wave, sr, _ = infer_process(
            ref_audio,
            r_text,
            tts_input,
            ema_model,
            vocoder,
            progress=None,
            speed=0.88,          # 庄严稳重语速
            target_rms=0.22,
            nfe_step=16
        )
        trimmed = trim_silence(wave, sr)
        print(f"   ✅ 完成! 耗时: {time.time() - t0:.2f}s, 音频时长: {len(trimmed)/sr:.2f}s", flush=True)
        para_records.append((p, trimmed, sr))

    print("\n==================================================", flush=True)
    print("🎼 正在组装全篇音频并精确计算 27 段落时间轴...", flush=True)
    print("==================================================", flush=True)

    full_audio = []
    current_time = 0.35  # 开篇静音 0.35s
    full_audio.append(np.zeros(int(0.35 * sr_target), dtype=np.float32))

    for idx, (p, p_wave, sr) in enumerate(para_records):
        p_id = p["id"]
        p_dur = len(p_wave) / sr
        p_start = round(current_time, 3)
        p_end = round(current_time + p_dur, 3)

        p["startTime"] = p_start
        p["endTime"] = p_end

        # 更新 lines 与 chars（多行段落按字数精准分配行起止时间）
        lines = p.get("lines", [])
        line_char_counts = []
        for line in lines:
            valid = [c for c in line.get("chars", []) if c.get("text", "").strip() and c.get("text") not in "，。！？；：、"]
            line_char_counts.append(max(1, len(valid)))
        total_valid = sum(line_char_counts) if line_char_counts else 1

        cur_l_time = p_start
        for l_idx, (line, count) in enumerate(zip(lines, line_char_counts)):
            l_dur = (count / total_valid) * p_dur
            l_start = round(cur_l_time, 3)
            l_end = round(p_end, 3) if l_idx == len(lines) - 1 else round(cur_l_time + l_dur, 3)

            line["lineStart"] = l_start
            line["lineEnd"] = l_end

            chars = line.get("chars", [])
            valid_chars = [c for c in chars if c.get("text", "").strip() and c.get("text") not in "，。！？；：、"]
            c_count = max(1, len(valid_chars))
            c_dur = (l_end - l_start) / c_count
            c_time = l_start
            for c in chars:
                if c.get("text", "").strip() and c.get("text") not in "，。！？；：、":
                    c["startTime"] = round(c_time, 3)
                    c["endTime"] = round(c_time + c_dur, 3)
                    c_time += c_dur

            cur_l_time = l_end

        full_audio.append(p_wave)
        current_time = p_end

        # 插入停顿：大段落停顿 0.55s，小分句停顿 0.35s
        if idx < len(para_records) - 1:
            pause_sec = 0.55 if p_id in MAJOR_SECTION_ENDS else 0.35
            pause_samples = np.zeros(int(pause_sec * sr_target), dtype=np.float32)
            full_audio.append(pause_samples)
            current_time += pause_sec

    # 结尾留白 1.0s
    full_audio.append(np.zeros(int(1.0 * sr_target), dtype=np.float32))
    concat_wave = np.concatenate(full_audio)

    # 导出文件
    out_wav = os.path.join(PROJECT_ROOT, "public", "audio", "xinjing_new.wav")
    out_mp3 = os.path.join(PROJECT_ROOT, "public", "audio", "xinjing.mp3")

    sf.write(out_wav, concat_wave, sr_target)

    cmd = [
        "ffmpeg", "-y", "-i", out_wav.replace("\\", "/"),
        "-b:a", "192k",
        out_mp3.replace("\\", "/")
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"\n🎉 《心经》全篇音频生成完毕: {out_mp3} (总长: {len(concat_wave)/sr_target:.2f}s)", flush=True)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(chapter_data, f, ensure_ascii=False, indent=2)
    print(f"✨ 经文时间轴已更新: {json_path}", flush=True)

if __name__ == "__main__":
    main()
