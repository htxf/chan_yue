# -*- coding: utf-8 -*-
import json
from opencc import OpenCC

cc = OpenCC('t2s')

with open('scratch/chapter_scan_raw.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== 扫描 85 分钟到结尾的可能品名 ===")
for seg in data['segments']:
    if seg['start'] > 5500: # 约 91 分钟
        s = seg['start']
        txt = cc.convert(seg['text'])
        m = int(s // 60)
        sec = int(s % 60)
        if any(k in txt for k in ['十三', '品', '嘱', '累', '人天', '卷下', '毕']):
            print(f"[{m:02d}:{sec:02d} / {s:.1f}s - {seg['end']:.1f}s]: {txt}")

print(f"\n音频全长约: {data['segments'][-1]['end']:.1f}s ({int(data['segments'][-1]['end']//60)}m{int(data['segments'][-1]['end']%60)}s)")
