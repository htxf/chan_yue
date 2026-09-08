#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_sutra_master.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
《禅阅》工业级古籍佛经音频母带生成与毫秒级时间轴对齐引擎 v2.0 (全小句 SAPI 跑通标准)

设计原则：
1. 单一真理源（Single Source of Truth）：100% 动态读取 src/data/<book>/<chapter>.json 屏幕注音。
2. 小句级 SAPI 封装（Clause-Level Boxing）：按标点划分整句封装 <phoneme>，每个字的读音 100% 由经文注音驱动（般若必然读 bō rě，绝不读 bān）。
3. 严格标点气口留白：句号补偿 250ms（总计 ~1050ms），逗号补偿 380ms（总计 ~580ms），经题补偿 550ms。
4. 原生底层时间戳捕获：利用 Azure Speech SDK word_boundary 事件直接获取毫秒级物理边界，零转录误差。
5. 纯净高保真零滤镜直出：24kHz 160kbps MP3 原生直出，消除任何人工染色与共振。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
用法示例:
    # 默认女声（晓秋）全篇母带并回写时间轴
    python scripts/generate_sutra_master.py --book xinjing --chapter chapter_1

    # 央视正声男声（云扬）全篇生成
    python scripts/generate_sutra_master.py --book xinjing --chapter chapter_1 --voice yunyang --output public/audio/xinjing_yunyang.mp3

    # 自然大模型男声（Bo）全篇生成
    python scripts/generate_sutra_master.py --book xinjing --chapter chapter_1 --voice bo --output public/audio/xinjing_bo.mp3
"""

import os
import sys
import json
import shutil
import argparse
from typing import List, Dict, Tuple, Any
import azure.cognitiveservices.speech as speechsdk
from pydub import AudioSegment
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# 预设音色指纹矩阵
VOICE_PRESETS: Dict[str, str] = {
    # 女声音色
    "xiaoqiu": "zh-CN-XiaoqiuNeural",   # 主力女声：晓秋（中气充沛、声底厚实、沉稳不衰）
    "xiaoxiao": "zh-CN-XiaoxiaoNeural", # 备选女声：晓晓（温婉清秀）
    "female": "zh-CN-XiaoqiuNeural",
    # 男声音色
    "yunyang": "zh-CN-YunyangNeural",   # 👑 主力男声：云扬（央视国宝级播音正声、庄严正大、绝无拖尾降调）
    "bo": "zh-CN-Bo:MAI-Voice-2",       # 🌿 自然大模型男声：Bo（微软最新 MAI-Voice-2，真实自然人声）
    "yunyi": "zh-CN-Yunyi:DragonHDFlashLatestNeural", # 次时代高清：云逸 Dragon HD（古典国风诗意）
    "yunze": "zh-CN-YunzeNeural",       # 沉厚老者：云泽
    "yunjian": "zh-CN-YunjianNeural",   # 纪实居士：云健
    "yunye": "zh-CN-YunyeNeural",       # 温润文僧：云野
    "yunfeng": "zh-CN-YunfengNeural",   # 从容叙事：云枫
    "male": "zh-CN-YunyangNeural",      # 默认男声直接锁定为云扬
}


class PinyinSapiConverter:
    """
    负责将带调拼音（如 xiāng、bú、nuò、bō、rě）转译为微软 SAPI 音标格式（如 xiang 1、bu 2、nuo 4、bo 1、re 3）
    """
    TONE_MAP: Dict[str, Tuple[str, str]] = {
        'ā': ('a', '1'), 'á': ('a', '2'), 'ǎ': ('a', '3'), 'à': ('a', '4'),
        'ē': ('e', '1'), 'é': ('e', '2'), 'ě': ('e', '3'), 'è': ('e', '4'),
        'ī': ('i', '1'), 'í': ('i', '2'), 'ǐ': ('i', '3'), 'ì': ('i', '4'),
        'ō': ('o', '1'), 'ó': ('o', '2'), 'ǒ': ('o', '3'), 'ò': ('o', '4'),
        'ū': ('u', '1'), 'ú': ('u', '2'), 'ǔ': ('u', '3'), 'ù': ('u', '4'),
        'ǖ': ('v', '1'), 'ǘ': ('v', '2'), 'ǚ': ('v', '3'), 'ǜ': ('v', '4'),
        'ü': ('v', '5')
    }

    @classmethod
    def to_sapi(cls, pinyin: str) -> str:
        """转换单个带调拼音为 SAPI 词音素（单音节）"""
        if not pinyin:
            return ""
        tone = '5'
        clean = ""
        for char in pinyin:
            if char in cls.TONE_MAP:
                base, t = cls.TONE_MAP[char]
                clean += base
                tone = t
            else:
                clean += char
        return f"{clean} {tone}"


class PhoneticGatekeeperError(Exception):
    """佛门正音与变调门禁拦截异常"""
    pass


def assert_phonetics_gatekeeper(data: Dict[str, Any]):
    """
    【强制安全门禁】：生成前 100% 自动化校验经文数据，不合规绝对阻断落盘
    1. 般若: bō rě
    2. 空相: xiāng
    3. 行识: shí
    4. 耨: nuò
    5. 不字变调: 遇四声必须为 bú，其余必须为 bù
    """
    errors = []
    for p in data.get('paragraphs', []):
        for line in p.get('lines', []):
            chars = line.get('chars', [])
            for i, c in enumerate(chars):
                t = c.get('text', '')
                py = c.get('pinyin', '')
                prev_t = chars[i-1].get('text', '') if i > 0 else ''
                nxt_t = chars[i+1].get('text', '') if i + 1 < len(chars) else ''
                nxt_py = chars[i+1].get('pinyin', '') if i + 1 < len(chars) else ''

                if t == '相' and prev_t == '空' and py != 'xiāng':
                    errors.append(f"段落{p.get('id')}: 空相之'相'必须为 xiāng，当前为 {py}")
                if t == '若' and prev_t == '般' and py != 'rě':
                    errors.append(f"段落{p.get('id')}: 般若之'若'必须为 rě，当前为 {py}")
                if t == '般' and nxt_t == '若' and py != 'bō':
                    errors.append(f"段落{p.get('id')}: 般若之'般'必须为 bō，当前为 {py}")
                if t == '识' and prev_t == '行' and py != 'shí':
                    errors.append(f"段落{p.get('id')}: 行识之'识'必须为 shí，当前为 {py}")
                if t == '耨' and py != 'nuò':
                    errors.append(f"段落{p.get('id')}: 梵音'耨'必须为 nuò，当前为 {py}")
                if t == '不':
                    is_fourth = any(nxt_py.endswith(x) for x in ['4', 'à', 'è', 'ì', 'ò', 'ù', 'ǜ']) or nxt_py in ['yì', 'miè', 'gòu', 'jìng']
                    if is_fourth and py != 'bú':
                        errors.append(f"段落{p.get('id')}: '不{nxt_t}({nxt_py})'必须变调为 bú，当前为 {py}")
                    elif not is_fourth and py != 'bù':
                        errors.append(f"段落{p.get('id')}: '不{nxt_t}({nxt_py})'必须读四声 bù，当前为 {py}")

    if errors:
        raise PhoneticGatekeeperError("🚨 经文注音未通过自动化门禁，已阻断合成:\n" + "\n".join(errors))


class SutraSSMLCompiler:
    """
    负责将经文 JSON 数据编译为小句级封装的标准 SSML 文本（完全复刻女声跑通标准）
    """
    PAUSE_PUNCTUATIONS = {'，', '。', '；', '、', '：', '？', '！'}
    DECORATIVE_PUNCT = {'“', '”', '「', '」', '『', '』', '‘', '’', '（', '）', '《', '》', '—', '…', '·'}

    def __init__(self, data: Dict[str, Any], voice_name: str, rate: str = "-11%", volume: str = "+10%", style: str = None):
        assert_phonetics_gatekeeper(data)
        self.data = data
        self.voice_name = voice_name
        self.rate = rate
        self.volume = volume
        self.style = style
        self.clauses_meta: List[Tuple[str, List[Dict[str, Any]]]] = []

    def compile(self) -> Tuple[str, List[Tuple[str, List[Dict[str, Any]]]]]:
        """编译生成完整 SSML 及对应的小句元数据列表"""
        ssml_clauses: List[str] = []
        self.clauses_meta = []

        # 1. 编译经题（Title）
        title_chars = [c for c in self.data.get('title', []) if c.get('text', '').strip() and c.get('pinyin', '').strip()]
        if title_chars:
            t_text = "".join([c['text'] for c in title_chars])
            t_sapi = " ".join([PinyinSapiConverter.to_sapi(c.get('pinyin', '')) for c in title_chars])
            ssml_clauses.append(f'<phoneme alphabet="sapi" ph="{t_sapi}">{t_text}</phoneme>。<break time="550ms"/>')
            self.clauses_meta.append(('title', title_chars))

        # 2. 编译经文段落（Paragraphs）
        for p in self.data.get('paragraphs', []):
            lines = p.get('lines', [])
            for l_idx, line in enumerate(lines):
                curr_chars: List[Dict[str, Any]] = []
                curr_sapis: List[str] = []
                chars = line.get('chars', [])

                for c_idx, c in enumerate(chars):
                    txt = c.get('text', '')
                    py = c.get('pinyin', '')

                    if txt in self.PAUSE_PUNCTUATIONS:
                        if curr_chars:
                            self._append_clause(curr_chars, curr_sapis, ssml_clauses)
                            curr_chars, curr_sapis = [], []
                        
                        # 判断是否为段落末尾结句
                        is_end = (l_idx == len(lines) - 1) and (
                            c_idx == len(chars) - 1 or all(not x.get('pinyin') for x in chars[c_idx+1:])
                        )
                        self._append_pause(txt, ssml_clauses, is_sentence_end=is_end)
                    elif txt in self.DECORATIVE_PUNCT:
                        # 装饰标点不发音、不生成空 phoneme
                        continue
                    elif txt.strip() and py.strip():
                        curr_chars.append(c)
                        curr_sapis.append(PinyinSapiConverter.to_sapi(py))

                if curr_chars:
                    self._append_clause(curr_chars, curr_sapis, ssml_clauses)

        ssml_body = "\n            ".join(ssml_clauses)
        
        # 演播风格封装
        if self.style:
            content_inner = f"""<mstts:express-as style="{self.style}" styledegree="0.8">
            <prosody rate="{self.rate}" volume="{self.volume}">
                {ssml_body}
            </prosody>
        </mstts:express-as>"""
        else:
            content_inner = f"""<prosody rate="{self.rate}" volume="{self.volume}">
            {ssml_body}
        </prosody>"""

        full_ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="zh-CN">
    <voice name="{self.voice_name}">
        {content_inner}
    </voice>
</speak>"""
        return full_ssml, self.clauses_meta

    def _append_clause(self, chars: List[Dict[str, Any]], sapis: List[str], target: List[str]):
        """
        封装小句：整句封装为一个完整 SAPI 词序列，名相内部绝对零 break，字字相扣。
        针对“如来善护念诸菩萨 / 善付嘱诸菩萨”等紧邻对偶句，TTS 自注意力极易将第二句重复名相弱读（轻读、轻佻滑脱）。
        自动分离谓语与圣号宾语，赋予专属稳健中气加权（volume +15%, rate -14%），
        并对“菩萨”注入硬去声同音定调（“菩飒”），彻底破除口语轻声（·sa）滑脱先验，字字沉稳厚重。
        """
        c_text = "".join([x['text'] for x in chars])
        if c_text in ("如来善护念诸菩萨", "善付嘱诸菩萨"):
            split_idx = 5 if c_text.startswith("如来善护念") else 3
            part1_chars, part2_chars = chars[:split_idx], chars[split_idx:]
            part1_sapi = " ".join(sapis[:split_idx])
            part2_sapi = " ".join(sapis[split_idx:])
            # 对偶圣号宾语“诸菩萨”采用同音硬去声定调（“诸菩飒”），彻底破除口语轻声（·sa）滑脱先验
            part2_text = "".join([x["text"] for x in part2_chars]).replace("菩萨", "菩飒")
            
            target.append(f'<phoneme alphabet="sapi" ph="{part1_sapi}">{"".join([x["text"] for x in part1_chars])}</phoneme><prosody volume="+15%" rate="-14%"><phoneme alphabet="sapi" ph="{part2_sapi}">{part2_text}</phoneme></prosody>')
            self.clauses_meta.append(('clause', part1_chars))
            self.clauses_meta.append(('clause', part2_chars))
        else:
            c_sapi = " ".join(sapis)
            target.append(f'<phoneme alphabet="sapi" ph="{c_sapi}">{c_text}</phoneme>')
            self.clauses_meta.append(('clause', chars))

    def _append_pause(self, punct: str, target: List[str], is_sentence_end: bool = False):
        """
        依参考样例实测精准留白与古籍经文声学标点归一化（Acoustic Punctuation Normalization）：
        1. 绝不向 TTS 引擎输出现代情绪标点 '！' 或 '？'，防止触发剧烈惊叫破音（尖尖的）或质问上挑；
        2. 句号类 ('。' 或句末终结 '！' / '？')：声学平落 '。<break time="250ms"/>'（实测总留白 ~1000ms，沉稳落定）；
        3. 呼赞与疑问承接 ('！', '？', 冒号 '：', 分号 '；')：声学温和气口 '，<break time="380ms"/>'（实测总留白 ~580ms，从容深呼吸）；
        4. 顿号 ('、')：保留顿号自身，微歇 120ms（实测总留白 ~250ms），并列韵律紧凑自然，杜绝报菜名式大断裂。
        """
        if punct == '。' or is_sentence_end:
            target.append('。<break time="250ms"/>')
        elif punct == '、':
            target.append('、<break time="120ms"/>')
        else:
            target.append('，<break time="380ms"/>')


class SpeechMasterSynthesizer:
    """
    负责调用 Azure Speech SDK 进行高保真合成，并捕获底层物理时间戳
    """
    def __init__(self, key: str, region: str):
        self.speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Audio24Khz160KBitRateMonoMp3
        )

    def synthesize(self, ssml: str, output_path: str) -> List[Dict[str, Any]]:
        """执行合成并返回捕获到的词级物理事件"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config, audio_config=audio_config)

        events: List[Dict[str, Any]] = []

        def on_word_boundary(e):
            events.append({
                'text': e.text,
                'start': e.audio_offset / 10000000.0,
                'duration': e.duration.total_seconds()
            })

        synthesizer.synthesis_word_boundary.connect(on_word_boundary)
        result = synthesizer.speak_ssml_async(ssml).get()

        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise RuntimeError(f"Azure Speech 合成失败: {result.cancellation_details.error_details}")

        return events


class TimestampAligner:
    """
    负责将捕获的物理时间戳对齐分配给 JSON 字符、行与段落
    """
    PUNCT_FILTER = {'。', '，', '；', '：', '、', '？', '！', '」', '「', '“', '”', '『', '』', '‘', '’', '《', '》', '（', '）'}

    @classmethod
    def align_and_save(cls, data: Dict[str, Any], clauses_meta: List[Tuple[str, List[Dict[str, Any]]]],
                       word_events: List[Dict[str, Any]], json_path: str):
        """执行对齐并保存更新后的经文 JSON"""
        # 0. 先行数据净化：彻底清理所有非发音字符（无 pinyin 的标点/引号等）的残留时间戳，杜绝历史脏数据污染
        for p in data.get('paragraphs', []):
            for line in p.get('lines', []):
                for c in line.get('chars', []):
                    if not c.get('pinyin') or not c.get('pinyin').strip():
                        c.pop('startTime', None)
                        c.pop('endTime', None)

        # 过滤纯标点物理事件
        actual_clauses = [w for w in word_events if w['text'] not in cls.PUNCT_FILTER]

        # 逐小句按字数等分对齐
        for i, (ctype, char_objs) in enumerate(clauses_meta):
            if i < len(actual_clauses):
                ev = actual_clauses[i]
                c_start = ev['start']
                c_dur = ev['duration']
                n_chars = len(char_objs)
                char_dur = c_dur / n_chars if n_chars > 0 else 0
                for j, c in enumerate(char_objs):
                    c['startTime'] = round(c_start + j * char_dur, 3)
                    c['endTime'] = round(c_start + (j + 1) * char_dur, 3)

        # 汇总段落与行时间戳（100% 仅从具有有效 pinyin 的发音汉字中提取）
        last_p_start = -1.0
        for p_idx, p in enumerate(data.get('paragraphs', [])):
            p_chars = [c for line in p.get('lines', []) for c in line.get('chars', []) if c.get('pinyin') and 'startTime' in c]
            if p_chars:
                p_start = p_chars[0]['startTime']
                p_end = p_chars[-1]['endTime']
                # 强制单调性门禁：段落时间严禁倒退
                if p_start < last_p_start:
                    raise ValueError(f"🚨 时间戳单调性异常熔断: 段落{p_idx} startTime ({p_start}) 小于前一段 ({last_p_start})")
                last_p_start = p_start
                p['startTime'] = p_start
                p['endTime'] = p_end

                last_l_start = -1.0
                for l_idx, line in enumerate(p.get('lines', [])):
                    l_chars = [c for c in line.get('chars', []) if c.get('pinyin') and 'startTime' in c]
                    if l_chars:
                        l_start = l_chars[0]['startTime']
                        l_end = l_chars[-1]['endTime']
                        if l_start < last_l_start:
                            raise ValueError(f"🚨 时间戳单调性异常熔断: 段落{p_idx} 行{l_idx} lineStart ({l_start}) 倒退")
                        last_l_start = l_start
                        line['lineStart'] = l_start
                        line['lineEnd'] = l_end

        # 汇总经题时间戳
        title_chars = [c for c in data.get('title', []) if c.get('pinyin') and 'startTime' in c]
        if title_chars:
            data['titleStart'] = title_chars[0]['startTime']
            data['titleEnd'] = title_chars[-1]['endTime']

        # 备份原 JSON 并写入
        shutil.copyfile(json_path, json_path + '.backup')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def resolve_voice_name(voice_arg: str) -> str:
    """解析音色参数，支持简写别名或完整名称"""
    key = voice_arg.lower().strip()
    return VOICE_PRESETS.get(key, voice_arg)


def generate_sutra_master(book: str, chapter: str, voice: str, output: str = None, 
                           update_json: bool = True, rate: str = "-11%"):
    """主流水线执行函数"""
    speech_key = os.environ.get('AZURE_SPEECH_KEY')
    service_region = os.environ.get('AZURE_SPEECH_REGION', 'eastasia')

    if not speech_key:
        raise ValueError("请在 .env 中配置 AZURE_SPEECH_KEY")

    json_path = os.path.join(PROJECT_ROOT, 'src', 'data', book, f"{chapter}.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"找不到经文 JSON 数据: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    actual_voice = resolve_voice_name(voice)
    
    # 针对音色自动绑定专属工业级风格与语速
    if "yunyang" in actual_voice.lower():
        auto_style = "narration-professional"
    elif "yunjian" in actual_voice.lower():
        auto_style = "documentary-narration"
    else:
        auto_style = None

    print(f"📖 正在加载经文: [{book} / {chapter}]")
    print(f"🎙️ 选定音色: {actual_voice} (输入别名: {voice}, 语速: {rate}, 演播风格: {auto_style})")

    # 1. 编译 SSML (经过强制数据门禁校验)
    compiler = SutraSSMLCompiler(data, actual_voice, rate=rate, volume="+10%", style=auto_style)
    ssml, clauses_meta = compiler.compile()

    # 2. 确定输出路径
    if not output:
        if book == "xinjing":
            output = os.path.join(PROJECT_ROOT, 'public', 'audio', 'xinjing.mp3')
        else:
            output = os.path.join(PROJECT_ROOT, 'public', 'audio', book, f"{chapter}.mp3")

    print(f"🚀 开始调用 Azure Speech 工业母带合成 -> {output}")
    synthesizer = SpeechMasterSynthesizer(speech_key, service_region)
    word_events = synthesizer.synthesize(ssml, output)

    # 3. 统计音频时长
    audio = AudioSegment.from_file(output)
    dur_sec = len(audio) / 1000.0
    print(f"✅ 合成成功！音频总时长: {dur_sec:.2f} 秒 ({dur_sec/60:.2f} 分钟)")

    # 4. 对齐并更新 JSON
    if update_json:
        print(f"⏱️ 正在回写毫秒级时间戳至 {json_path} ...")
        TimestampAligner.align_and_save(data, clauses_meta, word_events, json_path)
        print(f"✅ 毫秒级时间戳对齐与段落回写完成！(原文件已备份至 {json_path}.backup)")


def main():
    parser = argparse.ArgumentParser(description="《禅阅》工业级古籍佛经音频母带生成引擎 (女声全套跑通标准)")
    parser.add_argument("--book", default="xinjing", help="经书目录名 (默认: xinjing)")
    parser.add_argument("--chapter", default="chapter_1", help="章节文件名 (默认: chapter_1)")
    parser.add_argument("--voice", default="xiaoqiu", help="音色名称或别名 (xiaoqiu/yunyang/bo/yunyi/yunze/yunjian 等)")
    parser.add_argument("--rate", default="-11%", help="语速设置 (默认: -11%%)")
    parser.add_argument("--output", default=None, help="自定义音频输出路径 (默认: public/audio/<book>.mp3)")
    parser.add_argument("--no-update-json", action="store_true", help="禁止自动回写毫秒级时间戳到经文 JSON")

    args = parser.parse_args()
    generate_sutra_master(
        book=args.book,
        chapter=args.chapter,
        voice=args.voice,
        rate=args.rate,
        output=args.output,
        update_json=not args.no_update_json
    )


if __name__ == "__main__":
    main()
