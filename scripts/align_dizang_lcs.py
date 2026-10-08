# -*- coding: utf-8 -*-
"""
基于 Whisper + OpenCC + difflib.SequenceMatcher 全局 LCS 对齐的地藏经音频时间轴生成器
"""
import os
import json
import re
import difflib
import whisper
from opencc import OpenCC
import pypinyin

cc = OpenCC('t2s')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'src', 'data', 'dizangjing')
AUDIO_DIR = os.path.join(PROJECT_ROOT, 'public', 'audio', 'dizangjing')

def align_single_chapter(model, ch_idx):
    ch_id = f"chapter_{ch_idx}"
    json_path = os.path.join(DATA_DIR, f"{ch_id}.json")
    audio_path = os.path.join(AUDIO_DIR, f"{ch_id}.mp3")

    if not os.path.exists(json_path) or not os.path.exists(audio_path):
        print(f"跳过 {ch_id}: 文件不存在 ({json_path} 或 {audio_path})")
        return False

    print(f"\n=======================================================")
    print(f"正在对齐 {ch_id} ({audio_path})...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. Whisper word_timestamps 转写
    res = model.transcribe(audio_path, language='zh', word_timestamps=True, verbose=False)
    
    # 提取 ASR 字流 (转为简体)
    asr_chars = []
    for seg in res['segments']:
        words = seg.get('words', [])
        for w in words:
            clean = cc.convert(re.sub(r'[^\w]', '', w['word'].strip()))
            if not clean:
                continue
            w_start = w['start']
            w_end = w['end']
            w_dur = max(0.04, (w_end - w_start) / len(clean))
            for ci, ch in enumerate(clean):
                asr_chars.append({
                    'char': ch,
                    'start': round(w_start + ci * w_dur, 3),
                    'end': round(w_start + (ci + 1) * w_dur, 3)
                })

    print(f"  ASR 识别字数: {len(asr_chars)}")

    # 2. 收集 JSON 中有效经文字符
    json_char_objs = []
    for p in data['paragraphs']:
        for line in p['lines']:
            for c in line['chars']:
                if 'pinyin' in c and c.get('text'):
                    json_char_objs.append(c)

    print(f"  JSON 目标字数: {len(json_char_objs)}")

    json_text = ''.join(c['text'] for c in json_char_objs)
    asr_text = ''.join(c['char'] for c in asr_chars)

    # 3. 全局 LCS 匹配
    matcher = difflib.SequenceMatcher(None, json_text, asr_text)
    matching_blocks = matcher.get_matching_blocks()

    matched_count = 0
    for i, j, size in matching_blocks:
        for k in range(size):
            ti = i + k
            aj = j + k
            if ti < len(json_char_objs) and aj < len(asr_chars):
                json_char_objs[ti]['startTime'] = asr_chars[aj]['start']
                json_char_objs[ti]['endTime'] = asr_chars[aj]['end']
                matched_count += 1

    match_rate = (matched_count / len(json_char_objs)) * 100
    print(f"  全局 LCS 直接匹配率: {matched_count}/{len(json_char_objs)} ({match_rate:.1f}%)")

    # 4. 健壮双向线性插值填补未命中字
    anchors = []
    for idx, c in enumerate(json_char_objs):
        if c.get('startTime') is not None:
            anchors.append((idx, c['startTime'], c['endTime']))

    if len(anchors) < 2:
        print(f"  [ERROR] {ch_id} 匹配锚点过少 ({len(anchors)})，无法对齐！")
        return False

    # 头部插值 (首段前可能有播音员报幕，平滑过渡到第 1 个锚点)
    if anchors[0][0] > 0:
        first_idx, first_start, _ = anchors[0]
        step = max(0.12, (first_start - 0.2) / (first_idx + 1))
        for k in range(first_idx):
            json_char_objs[k]['startTime'] = round(max(0.0, first_start - (first_idx - k) * step), 3)
            json_char_objs[k]['endTime'] = round(max(0.05, first_start - (first_idx - k - 1) * step), 3)

    # 中间空隙插值
    for a_idx in range(len(anchors) - 1):
        idx1, s1, e1 = anchors[a_idx]
        idx2, s2, e2 = anchors[a_idx + 1]
        gap_count = idx2 - idx1 - 1
        if gap_count > 0:
            span = max(0.08 * gap_count, s2 - e1)
            step = span / (gap_count + 1)
            for k in range(1, gap_count + 1):
                cur_i = idx1 + k
                json_char_objs[cur_i]['startTime'] = round(e1 + (k - 1) * step, 3)
                json_char_objs[cur_i]['endTime'] = round(e1 + k * step, 3)

    # 尾部插值
    last_idx, _, last_end = anchors[-1]
    if last_idx < len(json_char_objs) - 1:
        step = 0.28
        cur_t = last_end
        for k in range(last_idx + 1, len(json_char_objs)):
            json_char_objs[k]['startTime'] = round(cur_t, 3)
            cur_t += step
            json_char_objs[k]['endTime'] = round(cur_t, 3)

    # 5. 单调递增安全平滑
    for k in range(len(json_char_objs) - 1):
        if json_char_objs[k]['endTime'] > json_char_objs[k + 1]['startTime']:
            mid = (json_char_objs[k]['endTime'] + json_char_objs[k + 1]['startTime']) / 2
            json_char_objs[k]['endTime'] = round(mid, 3)
            json_char_objs[k + 1]['startTime'] = round(mid, 3)

    # 6. 回算行与段落时间戳
    first_p_start = None
    for p in data['paragraphs']:
        for line in p['lines']:
            valid_chars = [c for c in line['chars'] if 'startTime' in c and c['startTime'] is not None]
            if valid_chars:
                line['lineStart'] = valid_chars[0]['startTime']
                line['lineEnd'] = valid_chars[-1]['endTime']
        
        valid_lines = [l for l in p['lines'] if 'lineStart' in l]
        if valid_lines:
            p['startTime'] = valid_lines[0]['lineStart']
            p['endTime'] = valid_lines[-1]['lineEnd']
            if first_p_start is None:
                first_p_start = p['startTime']

    # 经题 title 时间戳：从 0 开始到正文第 1 段前
    title_chars = data.get('title', [])
    if title_chars:
        head_dur = first_p_start if (first_p_start and first_p_start > 1.0) else 3.0
        t_step = (head_dur - 0.2) / max(1, len(title_chars))
        for ti, tc in enumerate(title_chars):
            tc['startTime'] = round(0.1 + ti * t_step, 3)
            tc['endTime'] = round(0.1 + (ti + 1) * t_step, 3)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_duration = data['paragraphs'][-1]['endTime']
    print(f"  ✓ {ch_id} 时间轴回写成功！")
    print(f"    - 段落数: {len(data['paragraphs'])}")
    print(f"    - 经题过渡: 0.0s -> {first_p_start:.2f}s")
    print(f"    - 全品终点: {total_duration:.2f}s ({int(total_duration//60)}m{int(total_duration%60)}s)")
    return True

if __name__ == '__main__':
    print("加载 Whisper base 模型中...")
    model = whisper.load_model('base')
    align_single_chapter(model, 1)
