# -*- coding: utf-8 -*-
import os
import re
import json
from opencc import OpenCC
import pypinyin

cc = OpenCC('t2s')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'src', 'data', 'dizangjing')
os.makedirs(DATA_DIR, exist_ok=True)

# 佛门经典专用多音字/名相正音词典 (词组级强匹配优先)
BUDDHIST_WORDS = {
    # 名号与菩萨名
    "地藏": ["dì", "zàng"],
    "地藏王": ["dì", "zàng", "wáng"],
    "菩萨": ["pú", "sà"],
    "摩诃萨": ["mó", "hē", "sà"],
    "摩诃": ["mó", "hē"],
    "文殊师利": ["wén", "shū", "shī", "lì"],
    "文殊": ["wén", "shū"],
    "普贤": ["pǔ", "xián"],
    "观音": ["guān", "yīn"],
    "观世音": ["guān", "shì", "yīn"],
    "弥勒": ["mí", "lè"],
    "定自在王": ["dìng", "zì", "zài", "wáng"],
    "大辩": ["dà", "biàn"],
    "无毒": ["wú", "dú"],
    "主命": ["zhǔ", "mìng"],
    
    # 经题与品名
    "忉利天": ["dāo", "lì", "tiān"],
    "忉利": ["dāo", "lì"],
    "阎浮提": ["yán", "fú", "tí"],
    "阎浮": ["yán", "fú"],
    "阎罗": ["yán", "luó"],
    "娑婆": ["suō", "pó"],
    "业缘": ["yè", "yuán"],
    "业感": ["yè", "gǎn"],
    "业相": ["yè", "xiàng"],
    "业障": ["yè", "zhàng"],

    # 佛名与刹土
    "拘留孙佛": ["jū", "liú", "sūn", "fó"],
    "拘那含牟尼佛": ["jū", "nà", "hán", "móu", "ní", "fó"],
    "迦叶佛": ["jiā", "shè", "fó"],
    "迦叶": ["jiā", "shè"],
    "狮子奋迅具足万行如来": ["shī", "zi", "fèn", "xùn", "jù", "zú", "wàn", "hèng", "rú", "lái"],
    "觉华定自在王如来": ["jué", "huá", "dìng", "zì", "zài", "wáng", "rú", "lái"],
    "清净莲华目如来": ["qīng", "jìng", "lián", "huá", "mù", "rú", "lái"],

    # 术语与梵音
    "般若": ["bō", "rě"],
    "波罗蜜": ["bō", "luó", "mì"],
    "波罗蜜多": ["bō", "luó", "mì", "duō"],
    "檀波罗蜜": ["tán", "bō", "luó", "mì"],
    "尸波罗蜜": ["shī", "bō", "luó", "mì"],
    "羼提波罗蜜": ["chàn", "tí", "bō", "luó", "mì"],
    "羼提": ["chàn", "tí"],
    "毗离耶": ["pí", "lí", "yē"],
    "毗离耶波罗蜜": ["pí", "lí", "yē", "bō", "luó", "mì"],
    "禅波罗蜜": ["chán", "bō", "luó", "mì"],
    "阿耨多罗": ["ā", "nuò", "duō", "luó"],
    "三藐三菩提": ["sān", "miǎo", "sān", "pú", "tí"],
    "那由他": ["nà", "yóu", "tā"],
    "阿僧祇": ["ā", "sēng", "qí"],
    "由旬": ["yóu", "xún"],
    "俱胝": ["jù", "zhī"],
    "伽陀": ["qié", "tuó"],
    "兜率陀天": ["dōu", "shuài", "tuó", "tiān"],
    "兜率": ["dōu", "shuài"],
    "摩醯首罗": ["mó", "xī", "shǒu", "luó"],
    "夜叉": ["yè", "chā"],
    "罗刹": ["luó", "chà"],
    "恶趣": ["è", "qù"],
    "恶道": ["è", "dào"],
    "泥犁": ["ní", "lí"],
    "阿鼻": ["ā", "bí"],
    "无间": ["wú", "jiàn"],
    "无间地狱": ["wú", "jiàn", "dì", "yù"],
    "大铁围山": ["dà", "tiě", "wéi", "shān"],
    "铁围山": ["tiě", "wéi", "shān"],
    
    # 人物与因缘
    "婆罗门女": ["pó", "luó", "mén", "nǚ"],
    "婆罗门": ["pó", "luó", "mén"],
    "光目女": ["guāng", "mù", "nǚ"],
    "光目": ["guāng", "mù"],
    "悦帝利": ["yuè", "dì", "lì"],

    # 常用佛门正音
    "南无": ["nā", "mó"],
    "称念": ["chēng", "niàn"],
    "供养": ["gòng", "yàng"],
    "舍利": ["shè", "lì"],
    "赞叹": ["zàn", "tàn"],
    "受持": ["shòu", "chí"],
    "读诵": ["dú", "sòng"],
    "如法": ["rú", "fǎ"],
    "法相": ["fǎ", "xiàng"],
    "实相": ["shí", "xiàng"],
    "空相": ["kōng", "xiāng"],
    "刚强": ["gāng", "qiáng"],
    "调伏": ["tiáo", "fú"],
    "方便": ["fāng", "biàn"],
    "宿命": ["sù", "mìng"],
    "福报": ["fú", "bào"],
    "胜妙": ["shèng", "miào"],
}

# 单字强制修正
BUDDHIST_CHARS = {
    "藏": "zàng",
    "萨": "sà",
    "刹": "chà",
    "那": "nà",
    "阿": "ā",
    "梵": "fàn",
    "牟": "móu",
    "伽": "qié",
    "迦": "jiā",
    "叶": "shè",
    "提": "tí",
    "度": "dù",
    "行": "xíng",
    "相": "xiàng",
    "识": "shí",
    "重": "zhòng",
    "难": "nán",
    "为": "wéi",
    "更": "gèng",
    "幢": "chuáng",
    "幡": "fān",
    "祇": "qí",
    "解": "jiě",
    "脱": "tuō",
    "应": "yìng",
    "调": "tiáo",
    "数": "shù",
    "佛": "fó",
    "华": "huá",
    "处": "chù",
    "降": "xiáng",
    "强": "qiáng",
}

TONE_MARKS = {'ā': 1, 'á': 2, 'ǎ': 3, 'à': 4,
              'ē': 1, 'é': 2, 'ě': 3, 'è': 4,
              'ī': 1, 'í': 2, 'ǐ': 3, 'ì': 4,
              'ō': 1, 'ó': 2, 'ǒ': 3, 'ò': 4,
              'ū': 1, 'ú': 2, 'ǔ': 3, 'ù': 4,
              'ǖ': 1, 'ǘ': 2, 'ǚ': 3, 'ǜ': 4}

def get_tone(py_str):
    if not py_str:
        return 0
    for ch, t in TONE_MARKS.items():
        if ch in py_str:
            return t
    return 0

def convert_sentence_to_chars(text):
    """将文本切分为字符，并精准匹配拼音与'不'字变调"""
    n = len(text)
    pinyins = [None] * n

    # 1. 词组级优先正音匹配
    i = 0
    while i < n:
        matched = False
        for l in range(12, 1, -1):
            if i + l <= n:
                sub = text[i:i+l]
                if sub in BUDDHIST_WORDS:
                    w_pys = BUDDHIST_WORDS[sub]
                    for idx, py in enumerate(w_pys):
                        pinyins[i + idx] = py
                    i += l
                    matched = True
                    break
        if not matched:
            i += 1

    # 2. 单字兜底 pypinyin
    for i, ch in enumerate(text):
        if pinyins[i] is not None:
            continue
        if ch in BUDDHIST_CHARS:
            pinyins[i] = BUDDHIST_CHARS[ch]
        elif re.match(r'[\u4e00-\u9fa5]', ch):
            py = pypinyin.pinyin(ch, style=pypinyin.Style.TONE)[0][0]
            pinyins[i] = py

    # 3. '不'字变调（后字为去声四声，读 bú；否则读 bù）
    for i, ch in enumerate(text):
        if ch == '不':
            next_tone = 0
            for j in range(i + 1, n):
                if re.match(r'[\u4e00-\u9fa5]', text[j]):
                    next_py = pinyins[j]
                    next_tone = get_tone(next_py)
                    break
            if next_tone == 4:
                pinyins[i] = 'bú'
            else:
                pinyins[i] = 'bù'

    # 组装结果结构
    chars = []
    for i, ch in enumerate(text):
        if re.match(r'[\u4e00-\u9fa5]', ch):
            chars.append({
                "text": ch,
                "pinyin": pinyins[i] or ""
            })
        else:
            chars.append({
                "text": ch
            })
    return chars

# 读取原始底本并提取前四品
with open('scripts/dizang_kanripo_001.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# 移除注释行
lines = []
for line in text.splitlines():
    if line.startswith('#') or line.startswith('No.') or line.startswith('《'):
        continue
    lines.append(line)
raw = '\n'.join(lines)
raw = re.sub(r'<pb:[^>]+>', '', raw)
raw = raw.replace('¶', '')

parts = re.split(r'\n\*\s+', raw)

# 目录定义
chapters_meta = [
    {"id": "chapter_1", "title": "第一品 忉利天宫神通品", "volume": "卷上", "part_idx": 1},
    {"id": "chapter_2", "title": "第二品 分身集会品", "volume": "卷上", "part_idx": 2},
    {"id": "chapter_3", "title": "第三品 观众生业缘品", "volume": "卷上", "part_idx": 3},
    {"id": "chapter_4", "title": "第四品 阎浮众生业感品", "volume": "卷上", "part_idx": 4},
    {"id": "chapter_5", "title": "第五品 地狱名号品", "volume": "卷中", "part_idx": 5},
    {"id": "chapter_6", "title": "第六品 如来赞叹品", "volume": "卷中", "part_idx": 6},
    {"id": "chapter_7", "title": "第七品 利益存亡品", "volume": "卷中"},
    {"id": "chapter_8", "title": "第八品 阎罗王众赞叹品", "volume": "卷中"},
    {"id": "chapter_9", "title": "第九品 称佛名号品", "volume": "卷中"},
    {"id": "chapter_10", "title": "第十品 校量布施功德缘品", "volume": "卷下"},
    {"id": "chapter_11", "title": "第十一品 地神护法品", "volume": "卷下"},
    {"id": "chapter_12", "title": "第十二品 见闻利益品", "volume": "卷下"},
    {"id": "chapter_13", "title": "第十三品 嘱累人天品", "volume": "卷下"},
]

# 1. 构建并写出 index.json
title_chars = convert_sentence_to_chars("地藏菩萨本愿经")
author_chars = convert_sentence_to_chars("唐于阗三藏沙门实叉难陀译")

index_json_data = {
    "id": "dizangjing",
    "title": title_chars,
    "author": author_chars,
    "chapters": chapters_meta
}

with open(os.path.join(DATA_DIR, 'index.json'), 'w', encoding='utf-8') as f:
    json.dump(index_json_data, f, ensure_ascii=False, indent=2)
print('Successfully generated dizangjing/index.json')

# 2. 构建前 4 品
for meta in chapters_meta[:4]:
    idx = meta["part_idx"]
    part_content = parts[idx].strip()
    p_lines = [l.strip() for l in part_content.splitlines() if l.strip()]
    raw_title = p_lines[0]
    body_text = '\n'.join(p_lines[1:])
    
    # 繁转简
    simp_title = cc.convert(raw_title)
    simp_body = cc.convert(body_text)

    # 规范化标点与空白
    simp_body = re.sub(r'[ \t　]+', '', simp_body)
    simp_body = simp_body.replace('——', '，').replace('──', '，')

    # 按句号切为小段落（保持 150~300 字一段）
    # 先按自然句切分
    sentences = []
    for s in re.split(r'([。；！？])', simp_body):
        if not s: continue
        if s in '。；！？':
            if sentences:
                sentences[-1] += s
        else:
            sentences.append(s)

    # 组合成适度大小的段落 (每段约 3~5 句话)
    paragraphs = []
    cur_p_lines = []
    cur_char_count = 0
    p_id = 1

    for s in sentences:
        s = s.strip()
        if not s: continue
        line_chars = convert_sentence_to_chars(s)
        cur_p_lines.append({
            "chars": line_chars
        })
        cur_char_count += len(s)
        # 若累计字符超过 160 字且以句号结句，收为一段
        if cur_char_count >= 160 and s.endswith(('。', '！')):
            paragraphs.append({
                "id": p_id,
                "lines": cur_p_lines
            })
            p_id += 1
            cur_p_lines = []
            cur_char_count = 0

    if cur_p_lines:
        paragraphs.append({
            "id": p_id,
            "lines": cur_p_lines
        })

    # 品名字符
    title_display = meta["title"]
    title_chars = convert_sentence_to_chars(title_display)

    chapter_data = {
        "chapterId": meta["id"],
        "title": title_chars,
        "audioUrl": f"/audio/dizangjing/{meta['id']}.mp3",
        "paragraphs": paragraphs
    }

    ch_file = os.path.join(DATA_DIR, f"{meta['id']}.json")
    with open(ch_file, 'w', encoding='utf-8') as f:
        json.dump(chapter_data, f, ensure_ascii=False, indent=2)
    print(f"Generated {meta['id']}.json ({meta['title']}): {len(paragraphs)} paragraphs, {sum(len(l['chars']) for p in paragraphs for l in p['lines'])} chars")

