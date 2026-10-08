# -*- coding: utf-8 -*-
import json
from opencc import OpenCC

cc = OpenCC('t2s')

with open('scratch/chapter_scan_raw.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

rough_points = [
    (1, 24.0, "忉利天宫神通品第一"),
    (2, 872.0, "分身集会品第二"),
    (3, 1113.0, "观众生业缘品第三"),
    (4, 1487.0, "阎浮众生业感品第四"),
    (5, 2273.0, "地狱名号品第五"),
    (6, 2595.0, "如来赞叹品第六"),
]

for ch_idx, approx_t, name in rough_points:
    print(f"\n==================== 第 {ch_idx} 品: {name} (约 {approx_t}s) ====================")
    nearby = [s for s in data['segments'] if abs(s['start'] - approx_t) < 20]
    for seg in nearby:
        txt = cc.convert(seg['text'])
        print(f"  [{seg['start']:.2f}s - {seg['end']:.2f}s]: {txt}")
