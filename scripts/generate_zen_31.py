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
POEM_ENV = "d:/Projects/poem_project/.env"

def get_api_key():
    env_local = os.path.join(PROJECT_ROOT, ".env")
    for env_path in [env_local, POEM_ENV]:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("GEMINI_API_KEY", "")

client = genai.Client(api_key=get_api_key())

test_text = "如是我闻。意时，佛在赦卫国奇树几孤独园。尔时，世尊食时，浊衣持钵，入赦卫大城乞食。"

# 极简中性 Prompt，杜绝朗诵腔和过度情感起伏
prompt_zen = f"用平稳、自然、无修饰的普通话念读以下文字，语调平平、不带朗诵感：\n\n{test_text}"

SANCTUARY_PLUS_FILTER = (
    "highpass=f=70,"
    "equalizer=f=150:width_type=h:width=120:g=2.2,"
    "equalizer=f=10500:width_type=h:width=2500:g=2.8,"
    "aecho=0.80:0.75:80|160|260:0.22|0.12|0.06"
)

# 4 款 Google 官方经典音色
CANDIDATES = [
    ("zen_Aoede_31", "Aoede", "女性·温婉平实（极少修饰）"),
    ("zen_Zephyr_31", "Zephyr", "女性·清平轻柔（无戏剧感）"),
    ("zen_Charon_31", "Charon", "男性·深沉平稳（经典原声）"),
    ("zen_Fenrir_31", "Fenrir", "男性·平直清晰（字正腔圆）"),
]

out_dir = os.path.join(PROJECT_ROOT, "public", "audio", "showcase")
os.makedirs(out_dir, exist_ok=True)

print("🧘 正在使用 Gemini 3.1 Flash TTS 生成【平实/去表演腔】对比样音...", flush=True)

results = []

for file_id, voice_name, desc in CANDIDATES:
    print(f"🎙️ 正在生成: {voice_name} ({desc})...", flush=True)
    raw_wav = os.path.join(out_dir, f"{file_id}_raw.wav")
    final_mp3 = os.path.join(out_dir, f"{file_id}.mp3")

    for attempt in range(1, 4):
        try:
            res = client.models.generate_content(
                model="gemini-3.1-flash-tts-preview",
                contents=prompt_zen,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                        )
                    )
                )
            )
            cand = res.candidates[0]
            if cand.content and cand.content.parts:
                pcm = cand.content.parts[0].inline_data.data
                if isinstance(pcm, str):
                    pcm = base64.b64decode(pcm)
                with wave.open(raw_wav, "wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(24000)
                    wf.writeframes(pcm)

                tmp_wav = final_mp3 + ".tmp.wav"
                subprocess.run([
                    "ffmpeg", "-y", "-i", raw_wav.replace('\\', '/'),
                    "-af", SANCTUARY_PLUS_FILTER,
                    "-c:a", "pcm_s16le", tmp_wav.replace('\\', '/')
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                subprocess.run([
                    "ffmpeg", "-y", "-i", tmp_wav.replace('\\', '/'),
                    "-b:a", "192k", final_mp3.replace('\\', '/')
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                if os.path.exists(raw_wav): os.remove(raw_wav)
                if os.path.exists(tmp_wav): os.remove(tmp_wav)
                print(f"   ✅ {voice_name} ({file_id}) 生成成功！", flush=True)
                results.append((file_id, voice_name, desc, f"http://localhost:5173/audio/showcase/{file_id}.mp3"))
                break
            else:
                print(f"   ⚠️ 尝试 {attempt} 返回空，等待 15s...", flush=True)
                time.sleep(15)
        except Exception as e:
            print(f"   ⚠️ 尝试 {attempt} 异常: {e}，等待 25s...", flush=True)
            time.sleep(25)

    print("   ⏳ 安全间隔等待 15s...", flush=True)
    time.sleep(15)

print("\n🎉 全部平实/去情感样音已生成！", flush=True)
for fid, vname, desc, url in results:
    print(f"- {vname} ({desc}): {url}")
