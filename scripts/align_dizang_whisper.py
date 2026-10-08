# -*- coding: utf-8 -*-
"""
基于 Whisper word-level timestamps + OpenCC 简繁转换 + 拼音动态规划的经文高精度对齐器
"""
import os
import json
import re
import whisper
from opencc import OpenCC
import pypinyin

cc = OpenCC('t2s')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'src', 'data', 'dizangjing')
AUDIO_DIR = os.path.join(PROJECT_ROOT, 'public', 'audio', 'dizangjing')

def get_pinyin_tone(word):
    py_list = pypinyin.pinyin(word, style=pypinyin.Style.TONE3)
    return [p[0] for p in py_list]

def align_chapter(model, ch_idx):
    ch_id = f"chapter_{ch_idx}"
    json_path = os.path.join(DATA_DIR, f"{ch_id}.json")
    audio_path = os.path.join(AUDIO_DIR, f"{ch_id}.mp3")

    if not os.path.exists(json_path) or not os.path.exists(audio_path):
        print(f"跳过 {ch_id}: 文件不存在")
        return

    print(f"\n==============================")
    print(f"正在对齐 {ch_id} ({audio_path})...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 1. Whisper 转写提取带时间戳词流
    res = model.transcribe(audio_path, language='zh', word_timestamps=True, verbose=False)
    
    # 提取 ASR 字流并全部转为简体中文
    asr_chars = []
    for seg in res['segments']:
        words = seg.get('words', [])
        for w in words:
            word_text = w['word'].strip()
            # 过滤标点和空白，转换为简体
            clean_word = cc.convert(re.sub(r'[^\w]', '', word_text))
            if not clean_word:
                continue
            w_start = w['start']
            w_end = w['end']
            w_dur = max(0.04, (w_end - w_start) / max(1, len(clean_word)))
            
            pys = get_pinyin_tone(clean_word)
            for ci, ch in enumerate(clean_word):
                py = pys[ci] if ci < len(pys) else ''
                asr_chars.append({
                    'char': ch,
                    'pinyin': py,
                    'start': round(w_start + ci * w_dur, 3),
                    'end': round(w_start + (ci + 1) * w_dur, 3)
                })

    print(f"ASR 识别得到 {len(asr_chars)} 个有效字符打点 (已繁转简)。")

    # 2. 收集 JSON 中所有需要打点的有效汉字对象
    json_char_objs = []
    for p in data['paragraphs']:
        for line in p['lines']:
            for c in line['chars']:
                if 'pinyin' in c and c.get('text'):
                    json_char_objs.append(c)

    print(f"JSON 目标字数: {len(json_char_objs)}")

    # 3. 动态规划 / 滑动窗口弹性对齐（字形匹配 > 拼音匹配）
    asr_idx = 0
    matched_count = 0

    for i, target in enumerate(json_char_objs):
        tgt_ch = target['text']
        tgt_py = target.get('pinyin', '')
        
        # 在 asr_chars 的 [asr_idx, asr_idx + 24] 窗口内寻找最佳匹配
        best_match_idx = -1
        search_window = min(len(asr_chars), asr_idx + 24)
        
        # 优先 1：汉字字形完全匹配
        for j in range(asr_idx, search_window):
            if asr_chars[j]['char'] == tgt_ch:
                best_match_idx = j
                break
        
        # 优先 2：同音字匹配（应对 ASR 偶发同音白字）
        if best_match_idx == -1 and tgt_py:
            for j in range(asr_idx, search_window):
                # 去除声调比对纯拼音字母
                asr_py_clean = re.sub(r'[0-9]', '', asr_chars[j]['pinyin'])
                tgt_py_clean = re.sub(r'[0-9]', '', tgt_py)
                if asr_py_clean and asr_py_clean == tgt_py_clean:
                    best_match_idx = j
                    break
        
        if best_match_idx != -1:
            match = asr_chars[best_match_idx]
            target['startTime'] = match['start']
            target['endTime'] = match['end']
            asr_idx = best_match_idx + 1
            matched_count += 1
        else:
            target['startTime'] = None
            target['endTime'] = None

    match_rate = (matched_count / len(json_char_objs)) * 100
    print(f"直接精准匹配率: {matched_count}/{len(json_char_objs)} ({match_rate:.1f}%)")

    # 4. 健壮双向线性插值填补未命中字
    anchors = []
    for idx, c in enumerate(json_char_objs):
        if c.get('startTime') is not None:
            anchors.append((idx, c['startTime'], c['endTime']))

    if len(anchors) < 2:
        print("错误：锚点过少，无法插值对齐！")
        return

    # 头部插值
    if anchors[0][0] > 0:
        first_idx, first_start, _ = anchors[0]
        step = max(0.1, first_start / (first_idx + 1))
        for k in range(first_idx):
            json_char_objs[k]['startTime'] = round(k * step, 3)
            json_char_objs[k]['endTime'] = round((k + 1) * step, 3)

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
    if title_chars and first_p_start and first_p_start > 0:
        t_step = min(0.4, (first_p_start - 0.2) / len(title_chars))
        for ti, tc in enumerate(title_chars):
            tc['startTime'] = round(0.1 + ti * t_step, 3)
            tc['endTime'] = round(0.1 + (ti + 1) * t_step, 3)

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✓ {ch_id} 毫秒级时间轴回写成功！")
    print(f"  - 覆盖段落: {len(data['paragraphs'])} 段")
    print(f"  - 起止时间: 0.0s -> {data['paragraphs'][-1]['endTime']}s ({int(data['paragraphs'][-1]['endTime']//60)}m{int(data['paragraphs'][-1]['endTime']%60)}s)")

if __name__ == '__main__':
    print("加载对齐模型...")
    model = whisper.load_model('base')
    align_chapter(model, 1)
