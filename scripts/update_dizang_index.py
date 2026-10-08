# -*- coding: utf-8 -*-
import json

with open('src/data/dizangjing/index.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for ch in data['chapters']:
    ch['audioUrl'] = f"/audio/dizangjing/{ch['id']}.mp3"

with open('src/data/dizangjing/index.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✓ dizangjing/index.json updated with audioUrl for all 13 chapters!")
