import subprocess
import whisper

# 之前第1品TTS时长约12分钟左右，第2品预计在8分~16分区间（480s~960s）
# 我们截取 600s ~ 900s (10分~15分) 这5分钟测试定位第二品开头
subprocess.run([
    'ffmpeg', '-y', '-i', 'scratch/dizang_full.mp3',
    '-ss', '600', '-t', '300',
    '-ar', '16000', '-ac', '1',
    'scratch/ch2_search.wav'
], check=True)

model = whisper.load_model('base')
result = model.transcribe('scratch/ch2_search.wav', language='zh')
print("--- 搜索第二品 ---")
for seg in result['segments']:
    text = seg['text']
    t_start = 600 + seg['start']
    t_end = 600 + seg['end']
    if any(k in text for k in ['第二', '分身', '集會', '集会', '品']):
        print(f"★ [{t_start:.1f}s ({t_start//60:.0f}m{t_start%60:.0f}s) - {t_end:.1f}s]: {text}")
    elif seg['start'] % 30 < 5:
        print(f"  [{t_start:.1f}s]: {text[:20]}...")
