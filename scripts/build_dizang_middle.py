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

# 卷中 佛门经典专用多音字/名相正音词典 (词组级强匹配优先)
BUDDHIST_WORDS = {
    # 佛名品（第九品专有佛号）
    "无边身如来": ["wú", "biān", "shēn", "rú", "lái"],
    "宝性如来": ["bǎo", "xìng", "rú", "lái"],
    "波头摩胜如来": ["bō", "tóu", "mó", "shèng", "rú", "lái"],
    "狮子吼如来": ["shī", "zǐ", "hǒu", "rú", "lái"],
    "拘留孙佛": ["jū", "liú", "sūn", "fó"],
    "毗婆尸佛": ["pí", "pó", "shī", "fó"],
    "宝胜如来": ["bǎo", "shèng", "rú", "lái"],
    "宝相如来": ["bǎo", "xiàng", "rú", "lái"],
    "袈裟幢如来": ["jiā", "shā", "chuáng", "rú", "lái"],
    "大通山王如来": ["dà", "tōng", "shān", "wáng", "rú", "lái"],
    "净月佛": ["jìng", "yuè", "fó"],
    "山王佛": ["shān", "wáng", "fó"],
    "智胜佛": ["zhì", "shèng", "fó"],
    "净名王佛": ["jìng", "míng", "wáng", "fó"],
    "智成就佛": ["zhì", "chéng", "jiù", "fó"],
    "无上佛": ["wú", "shàng", "fó"],
    "妙声佛": ["miào", "shēng", "fó"],
    "满月佛": ["mǎn", "yuè", "fó"],
    "月面佛": ["yuè", "miàn", "fó"],
    "波头摩": ["bō", "tóu", "mó"],
    "袈裟幢": ["jiā", "shā", "chuáng"],
    "袈裟": ["jiā", "shā"],
    "毗婆尸": ["pí", "pó", "shī"],
    "拘留孙": ["jū", "liú", "sūn"],

    # 鬼王与神名（第八品专有名相）
    "阎罗天子": ["yán", "luó", "tiān", "zǐ"],
    "恶毒鬼王": ["è", "dú", "guǐ", "wáng"],
    "多恶鬼王": ["duō", "è", "guǐ", "wáng"],
    "大诤鬼王": ["dà", "zhèng", "guǐ", "wáng"],
    "白虎鬼王": ["bái", "hǔ", "guǐ", "wáng"],
    "血虎鬼王": ["xiě", "hǔ", "guǐ", "wáng"],
    "赤虎鬼王": ["chì", "hǔ", "guǐ", "wáng"],
    "散殃鬼王": ["sàn", "yāng", "guǐ", "wáng"],
    "飞身鬼王": ["fēi", "shēn", "guǐ", "wáng"],
    "电光鬼王": ["diàn", "guāng", "guǐ", "wáng"],
    "狼牙鬼王": ["láng", "yá", "guǐ", "wáng"],
    "千眼鬼王": ["qiān", "yǎn", "guǐ", "wáng"],
    "噉兽鬼王": ["dàn", "shòu", "guǐ", "wáng"],
    "负石鬼王": ["fù", "shí", "guǐ", "wáng"],
    "主耗鬼王": ["zhǔ", "hào", "guǐ", "wáng"],
    "主祸鬼王": ["zhǔ", "huò", "guǐ", "wáng"],
    "主食鬼王": ["zhǔ", "shí", "guǐ", "wáng"],
    "主财鬼王": ["zhǔ", "cái", "guǐ", "wáng"],
    "主畜鬼王": ["zhǔ", "chù", "guǐ", "wáng"],
    "主禽鬼王": ["zhǔ", "qín", "guǐ", "wáng"],
    "主兽鬼王": ["zhǔ", "shòu", "guǐ", "wáng"],
    "主魅鬼王": ["zhǔ", "mèi", "guǐ", "wáng"],
    "主产鬼王": ["zhǔ", "chǎn", "guǐ", "wáng"],
    "主命鬼王": ["zhǔ", "mìng", "guǐ", "wáng"],
    "主疾鬼王": ["zhǔ", "jí", "guǐ", "wáng"],
    "主险鬼王": ["zhǔ", "xiǎn", "guǐ", "wáng"],
    "十一眼鬼王": ["shí", "yī", "yǎn", "guǐ", "wáng"],
    "阿那咤王": ["ā", "nà", "zhà", "wáng"],
    "大阿那咤王": ["dà", "ā", "nà", "zhà", "wáng"],
    "大辩长者": ["dà", "biàn", "zhǎng", "zhě"],

    # 菩萨与尊者名
    "普贤菩萨": ["pǔ", "xián", "pú", "sà"],
    "普贤": ["pǔ", "xián"],
    "普广菩萨": ["pǔ", "guǎng", "pú", "sà"],
    "普广": ["pǔ", "guǎng"],
    "定自在王": ["dìng", "zì", "zài", "wáng"],
    "地藏菩萨": ["dì", "zàng", "pú", "sà"],
    "地藏": ["dì", "zàng"],
    "菩萨": ["pú", "sà"],
    "摩诃萨": ["mó", "hē", "sà"],
    "摩诃": ["mó", "hē"],
    "善知识": ["shàn", "zhī", "shí"],

    # 地狱名号与名相（第五品）
    "极无间": ["jí", "wú", "jiàn"],
    "大阿鼻": ["dà", "ā", "bí"],
    "阿鼻地狱": ["ā", "bí", "dì", "yù"],
    "阿鼻": ["ā", "bí"],
    "无间地狱": ["wú", "jiàn", "dì", "yù"],
    "无间": ["wú", "jiàn"],
    "铁蒺藜": ["tiě", "jí", "lí"],
    "四角": ["sì", "jiǎo"],
    "飞刀": ["fēi", "dāo"],
    "火箭": ["huǒ", "jiàn"],
    "夹山": ["jiā", "shān"],
    "通枪": ["tōng", "qiāng"],
    "铁车": ["tiě", "chē"],
    "铁床": ["tiě", "chuáng"],
    "铁牛": ["tiě", "niú"],
    "铁衣": ["tiě", "yī"],
    "千刃": ["qiān", "rèn"],
    "铁驴": ["tiě", "lǘ"],
    "洋铜": ["yáng", "tóng"],
    "抱柱": ["bào", "zhù"],
    "流火": ["liú", "huǒ"],
    "耕舌": ["gēng", "shé"],
    "锉首": ["cuò", "shǒu"],
    "烧脚": ["shāo", "jiǎo"],
    "啗眼": ["dàn", "yǎn"],
    "铁丸": ["tiě", "wán"],
    "诤论": ["zhèng", "lùn"],
    "铁鈇": ["tiě", "fū"],

    # 经典经句与专有名词（第六、七品）
    "十斋日": ["shí", "zhāi", "rì"],
    "七七日": ["qī", "qī", "rì"],
    "七分之中": ["qī", "fēn", "zhī", "zhōng"],
    "称扬赞叹": ["chēng", "yáng", "zàn", "tàn"],
    "称佛名号": ["chēng", "fó", "míng", "hào"],
    "称名": ["chēng", "míng"],
    "志心称念": ["zhì", "xīn", "chēng", "niàn"],
    "称念": ["chēng", "niàn"],
    "转读尊经": ["zhuàn", "dú", "zūn", "jīng"],
    "转读": ["zhuàn", "dú"],
    "每转一遍": ["měi", "zhuàn", "yí", "biàn"],
    "善利": ["shàn", "lì"],
    "脱获善利": ["tuō", "huò", "shàn", "lì"],
    "魍魉精魅": ["wǎng", "liǎng", "jīng", "mèi"],
    "精魅": ["jīng", "mèi"],
    "魍魉": ["wǎng", "liǎng"],
    "刹利": ["chà", "lì"],
    "长者": ["zhǎng", "zhě"],
    "大长者": ["dà", "zhǎng", "zhě"],
    "床枕": ["chuáng", "zhěn"],
    "食顷": ["shí", "qǐng"],
    "房舍": ["fáng", "shè"],
    "舍宅": ["shè", "zhái"],
    "宿殃": ["sù", "yāng"],
    "宿命": ["sù", "mìng"],
    "宿业": ["sù", "yè"],
    "宿世": ["sù", "shì"],
    "刚彊": ["gāng", "qiáng"],
    "难调难伏": ["nán", "tiáo", "nán", "fú"],
    "恶道": ["è", "dào"],
    "恶趣": ["è", "qù"],
    "好道": ["hǎo", "dào"],
    "伎乐": ["jì", "yuè"],
    "瞻礼": ["zhān", "lǐ"],
    "瞻礼赞叹": ["zhān", "lǐ", "zàn", "tàn"],
    "阎浮提": ["yán", "fú", "tí"],
    "阎浮": ["yán", "fú"],
    "阎罗": ["yán", "luó"],
    "娑婆": ["suō", "pó"],
    "南无": ["nā", "mó"],
    "阿僧祇": ["ā", "sēng", "qí"],
    "受持": ["shòu", "chí"],
    "读诵": ["dú", "sòng"],
    "为未来世": ["wèi", "wèi", "lái", "shì"],
    "更为念": ["gèng", "wèi", "niàn"],
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
    "啗": "dàn",
    "啖": "dàn",
    "锉": "cuò",
    "剉": "cuò",
    "鈇": "fū",
    "魉": "liǎng",
    "魍": "wǎng",
    "魅": "mèi",
    "枕": "zhěn",
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

parts1 = clean_and_split_parts('scripts/dizang_kanripo_001.txt')
parts2 = clean_and_split_parts('scripts/dizang_kanripo_002.txt')

middle_chapters = [
    {"id": "chapter_5", "title": "第五品 地狱名号品", "volume": "卷中", "raw_content": parts1[5]},
    {"id": "chapter_6", "title": "第六品 如来赞叹品", "volume": "卷中", "raw_content": parts1[6]},
    {"id": "chapter_7", "title": "第七品 利益存亡品", "volume": "卷中", "raw_content": parts2[1]},
    {"id": "chapter_8", "title": "第八品 阎罗王众赞叹品", "volume": "卷中", "raw_content": parts2[2]},
    {"id": "chapter_9", "title": "第九品 称佛名号品", "volume": "卷中", "raw_content": parts2[3]},
]

print("=== 构建《地藏经》（卷中·第5-9品）数据底本 ===")
for meta in middle_chapters:
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
        "paragraphs": paragraphs
    }

    ch_file = os.path.join(DATA_DIR, f"{cid}.json")
    with open(ch_file, 'w', encoding='utf-8') as f:
        json.dump(chapter_data, f, ensure_ascii=False, indent=2)
    total_chars = sum(len(l['chars']) for p in paragraphs for l in p['lines'])
    print(f"✅ 生成 {cid}.json ({meta['title']}): {len(paragraphs)} 段落, {total_chars} 字符")

# 更新 src/data/dizangjing/index.json
index_file = os.path.join(DATA_DIR, 'index.json')
with open(index_file, 'r', encoding='utf-8') as f:
    idx_data = json.load(f)

for ch in idx_data.get('chapters', []):
    ch_id = ch.get('id') or ch.get('chapterId')
    # 激活第 1-9 品
    if ch_id in ['chapter_1', 'chapter_2', 'chapter_3', 'chapter_4', 'chapter_5', 'chapter_6', 'chapter_7', 'chapter_8', 'chapter_9']:
        ch.pop('isUpcoming', None)
    else:
        ch['isUpcoming'] = True

with open(index_file, 'w', encoding='utf-8') as f:
    json.dump(idx_data, f, ensure_ascii=False, indent=2)
print("✅ 更新 dizangjing/index.json: 第 5-9 品已成功激活为就绪状态！")
