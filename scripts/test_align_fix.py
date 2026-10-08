# -*- coding: utf-8 -*-
import os
import json
import re
import difflib
import whisper
from opencc import OpenCC
import pypinyin

cc = OpenCC('t2s')
CACHE_FILE = 'scratch/asr_chapter_1.json'

if not os.path.exists(CACHE_FILE):
    print("ASR 缓存不存在，使用 whisper base 转写 chapter_1.mp3...")
    model = whisper.load_model('base')
    res = model.transcribe('public/audio/dizangjing/chapter_1.mp3', language='zh', word_timestamps=True, verbose=False)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False)
else:
    print(f"从缓存 {CACHE_FILE} 加载转写结果...")
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        res = json.load(f)

# 提取 ASR 字流
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

print(f"ASR 总字数: {len(asr_chars)}, ASR 尾部时间: {asr_chars[-1]['end']:.2f}s")

# 加载 JSON 经文
with open('src/data/dizangjing/chapter_1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

json_char_objs = []
for p in data['paragraphs']:
    for line in p['lines']:
        for c in line['chars']:
            if 'pinyin' in c and c.get('text'):
                # 关键：彻底清空旧时间戳！
                c['startTime'] = None
                c['endTime'] = None
                json_char_objs.append(c)

print(f"JSON 待匹配字数: {len(json_char_objs)}")

json_text = ''.join(c['text'] for c in json_char_objs)
asr_text = ''.join(c['char'] for c in asr_chars)

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
print(f"直接匹配率: {matched_count}/{len(json_char_objs)} ({match_rate:.1f}%)")

# 线性插值
anchors = []
for idx, c in enumerate(json_char_objs):
    if c.get('startTime') is not None:
        anchors.append((idx, c['startTime'], c['endTime']))

print(f"有效锚点数: {len(anchors)}")
print(f"首个锚点: idx={anchors[0][0]}, 字={json_char_objs[anchors[0][0]]['text']}, time={anchors[0][1]}s")
print(f"末个锚点: idx={anchors[-1][0]}, 字={json_char_objs[anchors[-1][0]]['text']}, time={anchors[-1][2]}s")

# 头部插值
if anchors[0][0] > 0:
    first_idx, first_start, _ = anchors[0]
    step = max(0.12, (first_start - 0.2) / (first_idx + 1))
    for k in range(first_idx):
        json_char_objs[k]['startTime'] = round(max(0.0, first_start - (first_idx - k) * step), 3)
        json_char_objs[k]['endTime'] = round(max(0.05, first_start - (first_idx - k - 1) * step), 3)

# 中间插值
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

# 单调安全平滑
for k in range(len(json_char_objs) - 1):
    if json_char_objs[k]['endTime'] > json_char_objs[k + 1]['startTime']:
        mid = (json_char_objs[k]['endTime'] + json_char_objs[k + 1]['startTime']) / 2
        json_char_objs[k]['endTime'] = round(mid, 3)
        json_char_objs[k + 1]['startTime'] = round(mid, 3)

# 检查终点与起点
print(f"平滑后起点: {json_char_objs[0]['startTime']}s, 终点: {json_char_objs[-1]['endTime']:.2f}s ({int(json_char_objs[-1]['endTime']//60)}m{int(json_char_objs[-1]['endTime']%60)}s)")

# 回写 line 与 paragraph
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

title_chars = data.get('title', [])
if title_chars:
    head_dur = first_p_start if (first_p_start and first_p_start > 1.0) else 3.0
    t_step = (head_dur - 0.2) / max(1, len(title_chars))
    for ti, tc in enumerate(title_chars):
        tc['startTime'] = round(0.1 + ti * t_step, 3)
        tc['endTime'] = round(0.1 + (ti + 1) * t_step, 3)

with open('src/data/dizangjing/chapter_1.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✓ 回写完成！第一段起播点:", first_p_start, "最后一段终点:", data['paragraphs'][-1]['endTime'])
