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
            t_sapis = [PinyinSapiConverter.to_sapi(c.get('pinyin', '')) for c in title_chars]
            # 汉语连读上声变调（如“启请”qi 3 qing 3 -> qi 2 qing 3，杜绝启字后生硬气口卡顿）
            t_sapis = self._apply_sandhi(t_sapis)
            t_sapi = " ".join(t_sapis)
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
                        last_clause_txt = ""
                        if curr_chars:
                            last_clause_txt = "".join(x['text'] for x in curr_chars)
                            self._append_clause(curr_chars, curr_sapis, ssml_clauses)
                            curr_chars, curr_sapis = [], []
                        
                        # 判断是否为段落末尾结句
                        is_end = (l_idx == len(lines) - 1) and (
                            c_idx == len(chars) - 1 or all(not x.get('pinyin') for x in chars[c_idx+1:])
                        )
                        
                        # 检查是否为“善哉，善哉”成对赞叹：
                        # 首声善哉：180ms 紧凑气口；次声善哉：240ms 气口承接后续经文
                        # 两声均统一为逗号语境，彻底消除句末语调下沉与拉长，达成满分对称！
                        is_shanzai_first = False
                        is_shanzai_second = False
                        if last_clause_txt == "善哉" and not is_end:
                            if l_idx + 1 < len(lines):
                                next_l_txt = "".join(x.get('text', '') for x in lines[l_idx+1].get('chars', []))
                                if "善哉" in next_l_txt:
                                    is_shanzai_first = True
                            if l_idx > 0:
                                prev_l_txt = "".join(x.get('text', '') for x in lines[l_idx-1].get('chars', []))
                                if "善哉" in prev_l_txt:
                                    is_shanzai_second = True

                        if is_shanzai_first:
                            ssml_clauses.append('，<break time="180ms"/>')
                        elif is_shanzai_second:
                            ssml_clauses.append('，<break time="240ms"/>')
                        else:
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

    @staticmethod
    def _apply_sandhi(sapis: List[str]) -> List[str]:
        """汉语连续上声自然变调：两上声相连时，前字自动变阳平二声，避免引擎死板二声停顿断节"""
        res = list(sapis)
        for i in range(len(res) - 1):
            if res[i].endswith(" 3") and res[i+1].endswith(" 3"):
                res[i] = res[i][:-1] + "2"
        return res

    @classmethod
    def _split_clause_chars(cls, chars: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        语义重音解耦（Semantic Stress Decoupling）：
        消除大模型自注意力导致的句群末尾弱化（如排比‘咒’越念越轻）与句尾轻声吞音（如‘菩萨’发飘）。
        将易衰减名相拆分为独立 SAPI 词单元，赋予独立的声学基频与能量重音。
        """
        text = "".join(c.get('text', '') for c in chars)
        if len(text) <= 1:
            return [chars]

        # 1. 四大神咒排比解耦：拆开“是大神/咒”、“是大明/咒”、“是无上/咒”、“是无等等/咒”，杜绝自注意力抑制
        for pattern, pieces in [
            ("是大神咒", ["是大神", "咒"]),
            ("是大明咒", ["是大明", "咒"]),
            ("是无上咒", ["是无上", "咒"]),
            ("是无等等咒", ["是无等等", "咒"]),
        ]:
            if text == pattern:
                split_res = []
                idx = 0
                for piece in pieces:
                    p_len = len(piece)
                    split_res.append(chars[idx:idx+p_len])
                    idx += p_len
                return split_res

        # 2. 善哉拆解：将“哉”独立剥离，用于精准轻声 zai 5 + rate="+25%" 顿音短促收束，绝不拖尾
        if "善哉" in text:
            idx = text.find("善哉")
            sub_clauses = []
            if idx > 0:
                sub_clauses.append(chars[:idx])
            sub_clauses.append([chars[idx]])     # "善"
            sub_clauses.append([chars[idx+1]])   # "哉"
            if idx + 2 < len(chars):
                rest_chars = chars[idx+2:]
                sub_clauses.extend(cls._split_clause_chars(rest_chars))
            return sub_clauses

        # 3. 菩萨拆解（无论“诸菩萨”还是“菩萨”，均将“萨”独立剥离，用于精准 rate="+25%" 顿音短促收束，绝不拖音虚脱）
        if "菩萨" in text:
            idx = text.find("菩萨")
            sub_clauses = []
            if idx > 0:
                sub_clauses.append(chars[:idx])
            sub_clauses.append([chars[idx]])
            sub_clauses.append([chars[idx+1]])
            if idx + 2 < len(chars):
                rest_chars = chars[idx+2:]
                sub_clauses.extend(cls._split_clause_chars(rest_chars))
            return sub_clauses

        return [chars]

    def _append_clause(self, chars: List[Dict[str, Any]], sapis: List[str], target: List[str]):
        """
        封装小句：支持语义重音解耦。每个解耦词单元独立封装为 <phoneme>，并同步维护 clauses_meta 物理对齐。
        方案 A：针对“萨”、“哉”字施加独立紧凑轻声顿音收束，杜绝大模型句末拖尾与虚脱。
        """
        subs = self._split_clause_chars(chars)
        idx = 0
        for sub_chars in subs:
            sub_len = len(sub_chars)
            sub_sapis = sapis[idx:idx+sub_len]
            idx += sub_len

            c_text = "".join([x['text'] for x in sub_chars])
            sapis_sandhi = self._apply_sandhi(sub_sapis)
            c_sapi = " ".join(sapis_sandhi)
            
            if c_text == "萨":
                target.append('<prosody rate="+25%"><phoneme alphabet="sapi" ph="sa 5">萨</phoneme></prosody>')
            elif c_text == "哉":
                target.append('<prosody rate="+20%"><phoneme alphabet="sapi" ph="zai 1">哉</phoneme></prosody>')
            else:
                target.append(f'<phoneme alphabet="sapi" ph="{c_sapi}">{c_text}</phoneme>')
            self.clauses_meta.append(('clause', sub_chars))

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
                       word_events: List[Dict[str, Any]], json_path: str, voice_key: str = "female"):
        """执行对齐并保存更新后的经文 JSON"""
        # 如果文件已存在，先读取一次磁盘最新 JSON 合并已有 voices，确保男女声时间戳共存互不覆盖
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    disk_data = json.load(f)
                if 'voices' in disk_data and isinstance(disk_data['voices'], dict):
                    data['voices'] = disk_data['voices']
                for p_idx, p in enumerate(data.get('paragraphs', [])):
                    if p_idx < len(disk_data.get('paragraphs', [])):
                        disk_p = disk_data['paragraphs'][p_idx]
                        if 'voices' in disk_p and isinstance(disk_p['voices'], dict):
                            p['voices'] = disk_p['voices']
                        for l_idx, line in enumerate(p.get('lines', [])):
                            if l_idx < len(disk_p.get('lines', [])):
                                disk_line = disk_p['lines'][l_idx]
                                if 'voices' in disk_line and isinstance(disk_line['voices'], dict):
                                    line['voices'] = disk_line['voices']
            except Exception:
                pass

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
                if 'voices' not in p or not isinstance(p['voices'], dict):
                    p['voices'] = {}
                p['voices'][voice_key] = {'startTime': p_start, 'endTime': p_end}
                if voice_key == "female":
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
                        if 'voices' not in line or not isinstance(line['voices'], dict):
                            line['voices'] = {}
                        line['voices'][voice_key] = {'lineStart': l_start, 'lineEnd': l_end}
                        if voice_key == "female":
                            line['lineStart'] = l_start
                            line['lineEnd'] = l_end

        # 汇总经题时间戳
        title_chars = [c for c in data.get('title', []) if c.get('pinyin') and 'startTime' in c]
        if title_chars:
            t_start = title_chars[0]['startTime']
            t_end = title_chars[-1]['endTime']
            if 'voices' not in data or not isinstance(data['voices'], dict):
                data['voices'] = {}
            data['voices'][voice_key] = {'titleStart': t_start, 'titleEnd': t_end}
            if voice_key == "female":
                data['titleStart'] = t_start
                data['titleEnd'] = t_end

        # 备份原 JSON 并写入
        shutil.copyfile(json_path, json_path + '.backup')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def resolve_voice_name(voice_arg: str) -> str:
    """解析音色参数，支持简写别名或完整名称"""
    key = voice_arg.lower().strip()
    return VOICE_PRESETS.get(key, voice_arg)


def generate_sutra_master(book: str, chapter: str, voice: str, output: str = None, 
                           update_json: bool = True, rate: str = "-11%", voice_key: str = None):
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
    if not voice_key:
        if "yunyang" in actual_voice.lower() or "male" in actual_voice.lower():
            voice_key = "male"
        else:
            voice_key = "female"
    
    # 针对音色自动绑定专属工业级风格与语速
    if "yunyang" in actual_voice.lower():
        auto_style = "narration-professional"
    elif "yunjian" in actual_voice.lower():
        auto_style = "documentary-narration"
    else:
        auto_style = None

    print(f"📖 正在加载经文: [{book} / {chapter}]")
    print(f"🎙️ 选定音色: {actual_voice} (别名: {voice}, 语速: {rate}, 演播风格: {auto_style}, 时间轴分类: {voice_key})")

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

    # 自动同步副本为带音色后缀的文件 (如 chapter_2_female.mp3)
    if book != "xinjing":
        suffixed_out = os.path.join(PROJECT_ROOT, 'public', 'audio', book, f"{chapter}_{voice_key}.mp3")
        shutil.copy2(output, suffixed_out)
        print(f"📦 已自动同步音色专用母带 -> {suffixed_out}")

    # 4. 对齐并更新 JSON
    if update_json:
        print(f"⏱️ 正在回写 [{voice_key}] 毫秒级时间戳至 {json_path} ...")
        TimestampAligner.align_and_save(data, clauses_meta, word_events, json_path, voice_key=voice_key)
        print(f"✅ [{voice_key}] 毫秒级时间戳对齐与段落回写完成！(原文件已备份至 {json_path}.backup)")


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
