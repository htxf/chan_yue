# -*- coding: utf-8 -*-
import subprocess
import whisper
import json
import re

print("加载 Whisper base 模型中...")
model = whisper.load_model('base')

# 13 品关键词定义
CHAPTER_PATTERNS = [
    (1, re.compile(r'(地藏菩薩|地藏菩萨|忉利天|神通品|第一)')),
    (2, re.compile(r'(分身.*集會|分身.*集会|第二品|第[二2]品|第二)')),
    (3, re.compile(r'(觀眾生|观众生|業緣|业缘|第三品|第[三3]品|第三)')),
    (4, re.compile(r'(閻浮.*業感|阎浮.*业感|第四品|第[四4]品|第四)')),
    (5, re.compile(r'(地獄.*名號|地狱.*名号|第五品|第[五5]品|第五)')),
    (6, re.compile(r'(如來.*讚歎|如来.*赞叹|第六品|第[六6]品|第六)')),
    (7, re.compile(r'(利益.*存亡|第七品|第[七7]品|第七)')),
    (8, re.compile(r'(閻羅.*讚歎|阎罗.*赞叹|第八品|第[八8]品|第八)')),
    (9, re.compile(r'(稱佛.*名號|称佛.*名号|第九品|第[九9]品|第九)')),
    (10, re.compile(r'(校量.*布施|第十品|第[十10]品|第十)')),
    (11, re.compile(r'(地神.*護法|地神.*护法|第十一品|第11品|第十一)')),
    (12, re.compile(r'(見聞.*利益|见闻.*利益|第十二品|第12品|第十二)')),
    (13, re.compile(r'(囑累.*人天|嘱累.*人天|第十三品|第13品|第十三)')),
]

audio_path = 'scratch/dizang_full.mp3'
print("开始转写音频以识别章节切点 (whisper base)...")
result = model.transcribe(audio_path, language='zh', verbose=False)

print(f"转写完成，共 {len(result['segments'])} 个音频片段。正在扫描品目边界...")

chapter_candidates = {i: [] for i in range(1, 14)}

for seg in result['segments']:
    t = seg['start']
    text = seg['text']
    for ch_idx, pattern in CHAPTER_PATTERNS:
        if pattern.search(text):
            chapter_candidates[ch_idx].append({
                'time': t,
                'end': seg['end'],
                'text': text
            })

with open('scratch/chapter_scan_raw.json', 'w', encoding='utf-8') as f:
    json.dump({
        'segments': result['segments'],
        'candidates': chapter_candidates
    }, f, ensure_ascii=False, indent=2)

print("\n=== 品目匹配候选 ===")
for ch_idx in range(1, 14):
    cands = chapter_candidates[ch_idx]
    print(f"\n【第 {ch_idx} 品候选】(共 {len(cands)} 个匹配):")
    for c in cands[:5]:
        m = int(c['time'] // 60)
        s = int(c['time'] % 60)
        print(f"  [{m:02d}:{s:02d} / {c['time']:.1f}s]: {c['text']}")
