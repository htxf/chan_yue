# -*- coding: utf-8 -*-
"""
地藏经十三品音频无损切割脚本
读取确定的 chapters_timeline.json，使用 ffmpeg 将 scratch/dizang_full.mp3
无损精准切分为 public/audio/dizangjing/chapter_1.mp3 ~ chapter_13.mp3
"""
import os
import json
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'public', 'audio', 'dizangjing')
os.makedirs(OUTPUT_DIR, exist_ok=True)

INPUT_AUDIO = os.path.join(PROJECT_ROOT, 'scratch', 'dizang_full.mp3')
TIMELINE_FILE = os.path.join(PROJECT_ROOT, 'scratch', 'chapters_timeline.json')

def slice_all_chapters():
    if not os.path.exists(TIMELINE_FILE):
        print(f"Error: {TIMELINE_FILE} not found!")
        return

    with open(TIMELINE_FILE, 'r', encoding='utf-8') as f:
        timeline = json.load(f)

    for item in timeline:
        ch_id = item['chapterId']
        start_t = item['startTime']
        end_t = item['endTime']
        title = item.get('title', ch_id)
        out_file = os.path.join(OUTPUT_DIR, f"{ch_id}.mp3")

        print(f"正在切割 {ch_id} ({title}): {start_t}s -> {end_t}s (时长: {end_t - start_t:.1f}s)...")
        # 采用高品质编码 24kHz / 160kbps 或直接 copy
        # 为了保证 web 播放兼容性和零首尾延迟，使用 libmp3lame 44.1kHz 160kbps
        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start_t),
            '-to', str(end_t),
            '-i', INPUT_AUDIO,
            '-c:a', 'libmp3lame',
            '-b:a', '160k',
            '-ar', '44100',
            out_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        size_mb = os.path.getsize(out_file) / (1024 * 1024)
        print(f"  ✓ 成功导出 {ch_id}.mp3 ({size_mb:.2f} MB)")

if __name__ == '__main__':
    slice_all_chapters()
