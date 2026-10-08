import subprocess
import whisper

# 截取前 120 秒为 wav
subprocess.run([
    'ffmpeg', '-y', '-i', 'scratch/dizang_full.mp3',
    '-ss', '00:00:00', '-t', '120',
    '-ar', '16000', '-ac', '1',
    'scratch/intro_test.wav'
], check=True)

# 用 whisper base 模型快速转写
model = whisper.load_model('base')
result = model.transcribe('scratch/intro_test.wav', language='zh')
print("--- 转写前 120 秒 ---")
for seg in result['segments']:
    print(f"[{seg['start']:.2f}s - {seg['end']:.2f}s]: {seg['text']}")
