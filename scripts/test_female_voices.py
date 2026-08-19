import os
import sys
import base64
import wave
import time
import subprocess
from google import genai
from google.genai import types

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_api_key():
    with open('d:/Projects/poem_project/.env', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('GEMINI_API_KEY='):
                return line.strip().split('=', 1)[1].strip().strip('"').strip("'")

client = genai.Client(api_key=get_api_key())

text = "如是我闻。意时，佛在赦卫国奇树几孤独园。尔时，世尊食时，浊衣持钵，入赦卫大城乞食。"
prompt = f"请用温婉、空灵、宁静、从容的标准普通话朗读以下经文，语调平和自然，字音准确，不急不缓：\n\n{text}"

SANCTUARY_PLUS_FILTER = (
    "highpass=f=70,"
    "equalizer=f=150:width_type=h:width=120:g=2.2,"
    "equalizer=f=10500:width_type=h:width=2500:g=2.8,"
    "aecho=0.80:0.75:80|160|260:0.22|0.12|0.06"
)

# Gemini 官方女性预设音色
FEMALE_VOICES = ['Aoede', 'Kore', 'Leda', 'Zephyr']

for voice in FEMALE_VOICES:
    print(f"正在生成女性音色: {voice}...", flush=True)
    try:
        res = client.models.generate_content(
            model="gemini-3.1-flash-tts-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)
                    )
                )
            )
        )
        cand = res.candidates[0]
        if cand.content and cand.content.parts:
            pcm = cand.content.parts[0].inline_data.data
            if isinstance(pcm, str):
                pcm = base64.b64decode(pcm)
            
            raw_wav = f"public/audio/test_female_{voice}_raw.wav"
            with wave.open(raw_wav, 'wb') as wf:
                wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000)
                wf.writeframes(pcm)
                
            out_mp3 = f"public/audio/test_female_{voice}.mp3"
            cmd = [
                'ffmpeg', '-y', '-i', raw_wav,
                '-af', SANCTUARY_PLUS_FILTER,
                '-b:a', '192k', out_mp3
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if os.path.exists(raw_wav):
                os.remove(raw_wav)
            print(f"✅ {voice} 生成成功: http://localhost:5173/audio/test_female_{voice}.mp3", flush=True)
            time.sleep(10)
    except Exception as e:
        print(f"❌ {voice} 生成失败: {e}", flush=True)
