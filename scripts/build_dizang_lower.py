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

# 卷下 佛门经典专用多音字/名相正音词典 (词组级强匹配优先)
BUDDHIST_WORDS = {
    # 菩萨与大士尊名
    "观世音菩萨": ["guān", "shì", "yīn", "pú", "sà"],
    "观世音": ["guān", "shì", "yīn"],
    "观音": ["guān", "yīn"],
    "虚空藏菩萨": ["xū", "kōng", "zàng", "pú", "sà"],
    "虚空藏": ["xū", "kōng", "zàng"],
    "坚牢地神": ["jiān", "láo", "dì", "shén"],
    "坚牢": ["jiān", "láo"],
    "地藏菩萨": ["dì", "zàng", "pú", "sà"],
    "地藏": ["dì", "zàng"],
    "菩萨": ["pú", "sà"],
    "摩诃萨": ["mó", "hē", "sà"],
    "摩诃": ["mó", "hē"],
    "大士": ["dà", "shì"],

    # 梵音与专有经名
    "阿耨多罗三藐三菩提": ["ā", "nuò", "duō", "luó", "sān", "miǎo", "sān", "pú", "tí"],
    "阿耨多罗": ["ā", "nuò", "duō", "luó"],
    "阿耨": ["ā", "nuò"],
    "三藐三菩提": ["sān", "miǎo", "sān", "pú", "tí"],
    "般若": ["bō", "rě"],
    "波罗蜜": ["bō", "luó", "mì"],
    "波罗蜜多": ["bō", "luó", "mì", "duō"],
    "校量布施": ["jiào", "liáng", "bù", "shī"],
    "校量": ["jiào", "liáng"],
    "布施": ["bù", "shī"],
    "嘱累人天": ["zhǔ", "lěi", "rén", "tiān"],
    "嘱累": ["zhǔ", "lěi"],
    "辟支佛": ["bì", "zhī", "fó"],
    "辟除": ["pì", "chú"],
    "转轮圣王": ["zhuàn", "lún", "shèng", "wáng"],
    "转轮王": ["zhuàn", "lún", "wáng"],
    "转轮": ["zhuàn", "lún"],
    "大毫相光": ["dà", "háo", "xiàng", "guāng"],
    "毫相光": ["háo", "xiàng", "guāng"],
    "毫相": ["háo", "xiàng"],
    "白毫相": ["bái", "háo", "xiàng"],
    "顶门": ["dǐng", "mén"],
    "涅槃乐": ["niè", "pán", "lè"],
    "涅槃": ["niè", "pán"],
    "二十八种利益": ["èr", "shí", "bā", "zhǒng", "lì", "yì"],
    "二十八": ["èr", "shí", "bā"],
    "七宝": ["qī", "bǎo"],
    "十斋日": ["shí", "zhāi", "rì"],
    "释梵": ["shì", "fàn"],
    "刹利": ["chà", "lì"],
    "婆罗门": ["pó", "luó", "mén"],
    "大长者": ["dà", "zhǎng", "zhě"],
    "长者": ["zhǎng", "zhě"],
    "居士": ["jū", "shì"],
    "宰辅": ["zǎi", "fǔ"],
    "大辩": ["dà", "biàn"],
    "无间": ["wú", "jiàn"],
    "阿鼻": ["ā", "bí"],
    "阿僧祇": ["ā", "sēng", "qí"],
    "由旬": ["yóu", "xún"],
    "阎浮提": ["yán", "fú", "tí"],
    "阎浮": ["yán", "fú"],
    "娑婆": ["suō", "pó"],
    "善知识": ["shàn", "zhī", "shí"],
    "南无": ["nā", "mó"],
    "供养": ["gòng", "yàng"],
    "受持": ["shòu", "chí"],
    "读诵": ["dú", "sòng"],
    "瞻礼": ["zhān", "lǐ"],
    "赞叹": ["zàn", "tàn"],
    "称念": ["chēng", "niàn"],
    "称名": ["chēng", "míng"],
    "舍宅": ["shè", "zhái"],
    "恶道": ["è", "dào"],
    "恶趣": ["è", "qù"],
    "好道": ["hǎo", "dào"],
    "善利": ["shàn", "lì"],
    "宿世": ["sù", "shì"],
    "宿殃": ["sù", "yāng"],
    "宿命": ["sù", "mìng"],
    "为未来世": ["wèi", "wèi", "lái", "shì"],
    "更不": ["gèng", "bù"],
    "难调难伏": ["nán", "tiáo", "nán", "fú"],
    "解脱": ["jiě", "tuō"],
}

# 单字强制正音
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
    "彊": "qiáng",
    "累": "lěi",
    "校": "jiào",
    "辟": "bì",
    "施": "shī",
    "耨": "nuò",
    "般": "bō",
    "若": "rě",
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

def clean_and_split_parts(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()
    lines = []
    for line in text.splitlines():
        if line.startswith('#') or line.startswith('No.') or line.startswith('《'):
            continue
        lines.append(line)
    raw = '\n'.join(lines)
    raw = re.sub(r'<pb:[^>]+>', '', raw)
    raw = raw.replace('¶', '')
    return re.split(r'\n\*\s+', raw)

parts2 = clean_and_split_parts('scripts/dizang_kanripo_002.txt')

lower_chapters = [
    {"id": "chapter_10", "title": "第十品 校量布施功德缘品", "volume": "卷下", "raw_content": parts2[4]},
    {"id": "chapter_11", "title": "第十一品 地神护法品", "volume": "卷下", "raw_content": parts2[5]},
    {"id": "chapter_12", "title": "第十二品 见闻利益品", "volume": "卷下", "raw_content": parts2[6]},
    {"id": "chapter_13", "title": "第十三品 嘱累人天品", "volume": "卷下", "raw_content": parts2[7]},
]

print("=== 构建《地藏经》（卷下·第10-13品）数据底本 ===")
for meta in lower_chapters:
    cid = meta["id"]
    content = meta["raw_content"].strip()
    p_lines = [l.strip() for l in content.splitlines() if l.strip()]
    raw_title = p_lines[0]
    body_text = '\n'.join(p_lines[1:])

    # 繁转简
    simp_title = cc.convert(raw_title)
    simp_body = cc.convert(body_text)

    # 规范化标点与空白换行（彻底移除古籍机械断行换行符）
    simp_body = re.sub(r'[\r\n \t　]+', '', simp_body)
    simp_body = simp_body.replace('——', '，').replace('──', '，')

    # 按自然句切分
    sentences = []
    for s in re.split(r'([。；！？])', simp_body):
        if not s: continue
        if s in '。；！？':
            if sentences:
                sentences[-1] += s
        else:
            sentences.append(s)

    # 组合成适度大小的段落 (累计约 160 字且以句号结句为一段)
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

    title_display = meta["title"]
    title_chars = convert_sentence_to_chars(title_display)

    chapter_data = {
        "chapterId": cid,
        "title": title_chars,
        "audioUrl": f"/audio/dizangjing/{cid}.mp3",
        "paragraphs": paragraphs
    }

    ch_file = os.path.join(DATA_DIR, f"{cid}.json")
    with open(ch_file, 'w', encoding='utf-8') as f:
        json.dump(chapter_data, f, ensure_ascii=False, indent=2)
    total_chars = sum(len(l['chars']) for p in paragraphs for l in p['lines'])
    print(f"✅ 生成 {cid}.json ({meta['title']}): {len(paragraphs)} 段落, {total_chars} 字符")

# 更新 src/data/dizangjing/index.json: 全部 13 品全部激活！
index_file = os.path.join(DATA_DIR, 'index.json')
with open(index_file, 'r', encoding='utf-8') as f:
    idx_data = json.load(f)

for ch in idx_data.get('chapters', []):
    ch.pop('isUpcoming', None)

with open(index_file, 'w', encoding='utf-8') as f:
    json.dump(idx_data, f, ensure_ascii=False, indent=2)
print("✅ 更新 dizangjing/index.json: 全卷十三品 100% 激活为正式就绪状态！")
