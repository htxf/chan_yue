import json
import os

index = []

# Xinjing
with open('src/data/xinjing/chapter_1.json', 'r', encoding='utf-8') as f:
    xj = json.load(f)
    snippets = []
    for p in xj.get('paragraphs', []):
        for line in p.get('lines', []):
            txt = ''.join(c.get('text', '') for c in line.get('chars', []))
            if txt.strip():
                snippets.append(txt.strip())
    index.append({
        'bookId': 'xinjing',
        'bookTitle': '般若波罗蜜多心经',
        'chapterId': 'chapter_1',
        'chapterTitle': '般若波罗蜜多心经',
        'snippets': snippets
    })

# Jingangjing
for i in range(1, 33):
    ch_id = f'chapter_{i}'
    path = f'src/data/jingangjing/{ch_id}.json'
    if not os.path.exists(path):
        continue
    with open(path, 'r', encoding='utf-8') as f:
        doc = json.load(f)
        ch_title = ''.join(c.get('text', '') if isinstance(c, dict) else str(c) for c in doc.get('title', []))
        snippets = []
        for p in doc.get('paragraphs', []):
            for line in p.get('lines', []):
                txt = ''.join(c.get('text', '') for c in line.get('chars', []))
                if txt.strip():
                    snippets.append(txt.strip())
        index.append({
            'bookId': 'jingangjing',
            'bookTitle': '金刚般若波罗蜜多经',
            'chapterId': ch_id,
            'chapterTitle': ch_title,
            'snippets': snippets
        })

with open('src/data/search_index.json', 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print("Generated search_index.json successfully! Chapters count:", len(index))
