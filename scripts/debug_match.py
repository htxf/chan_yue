# -*- coding: utf-8 -*-
import json
import re
from opencc import OpenCC
import whisper

cc = OpenCC('t2s')

with open('src/data/dizangjing/chapter_1.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

json_chars = []
for p in data['paragraphs']:
    for line in p['lines']:
        for c in line['chars']:
            if 'pinyin' in c and c.get('text'):
                json_chars.append(c['text'])

json_text = ''.join(json_chars)
print("=== JSON 经文前 120 字 ===")
print(json_text[:120])

# 加载之前转写的 segment
model = whisper.load_model('base')
res = model.transcribe('public/audio/dizangjing/chapter_1.mp3', language='zh', word_timestamps=True, verbose=False)

asr_words = []
for seg in res['segments']:
    words = seg.get('words', [])
    for w in words:
        clean = cc.convert(re.sub(r'[^\w]', '', w['word'].strip()))
        if clean:
            asr_words.append((clean, w['start'], w['end']))

asr_text = ''.join(w[0] for w in asr_words)
print("\n=== ASR 识别前 120 字 ===")
print(asr_text[:120])

print("\n=== ASR 识别最后 120 字 ===")
print(asr_text[-120:])

print("\n=== JSON 经文最后 120 字 ===")
print(json_text[-120:])
