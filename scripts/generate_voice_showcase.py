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

# 测试文本：金刚经开篇名句（含多音字校准）
test_text = "如是我闻。意时，佛在赦卫国奇树几孤独园。尔时，世尊食时，浊衣持钵，入赦卫大城乞食。"
prompt = f"用温和从容、典雅空灵的语气朗读以下古文经文：\n\n{test_text}"

SANCTUARY_PLUS_FILTER = (
    "highpass=f=70,"
    "equalizer=f=150:width_type=h:width=120:g=2.2,"
    "equalizer=f=10500:width_type=h:width=2500:g=2.8,"
    "aecho=0.80:0.75:80|160|260:0.22|0.12|0.06"
)

VOICE_CANDIDATES = [
    # 女性音色
    ("Aoede", "女性·温婉空灵", "gemini-2.5-flash-preview-tts"),
    ("Kore", "女性·清澈舒缓", "gemini-2.5-flash-preview-tts"),
    ("Leda", "女性·沉静典雅", "gemini-2.5-flash-preview-tts"),
    ("Zephyr", "女性·轻柔纯净", "gemini-2.5-flash-preview-tts"),
    # 男性音色
    ("Charon", "男性·深沉庄严（诗词原声）", "gemini-2.5-flash-preview-tts"),
    ("Fenrir", "男性·稳健清晰（标准正音）", "gemini-2.5-flash-preview-tts"),
    ("Orus", "男性·浑厚沉静（低沉共鸣）", "gemini-2.5-flash-preview-tts"),
    ("Puck", "男性·自然从容（平和叙事）", "gemini-2.5-flash-preview-tts"),
]

out_dir = os.path.join(PROJECT_ROOT, "public", "audio", "showcase")
os.makedirs(out_dir, exist_ok=True)

results = []

for voice_name, voice_desc, model_name in VOICE_CANDIDATES:
    print(f"🎙️ 正在生成【{voice_name} - {voice_desc}】...", flush=True)
    raw_wav = os.path.join(out_dir, f"{voice_name}_raw.wav")
    final_mp3 = os.path.join(out_dir, f"{voice_name}.mp3")

    success = False
    for attempt in range(1, 4):
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=prompt,
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

                # 施加古刹幽鸣声学滤镜
                tmp_wav = final_mp3 + ".tmp.wav"
                cmd1 = [
                    "ffmpeg", "-y", "-i", raw_wav.replace('\\', '/'),
                    "-af", SANCTUARY_PLUS_FILTER,
                    "-c:a", "pcm_s16le", tmp_wav.replace('\\', '/')
                ]
                subprocess.run(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                cmd2 = [
                    "ffmpeg", "-y", "-i", tmp_wav.replace('\\', '/'),
                    "-b:a", "192k", final_mp3.replace('\\', '/')
                ]
                subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                if os.path.exists(raw_wav): os.remove(raw_wav)
                if os.path.exists(tmp_wav): os.remove(tmp_wav)

                print(f"   ✅ {voice_name} 生成成功！", flush=True)
                results.append((voice_name, voice_desc, f"http://localhost:5173/audio/showcase/{voice_name}.mp3"))
                success = True
                break
            else:
                print(f"   ⚠️ 尝试 {attempt}: 返回空 (FinishReason={cand.finish_reason})，等待 10s...", flush=True)
                time.sleep(10)
        except Exception as e:
            print(f"   ⚠️ 尝试 {attempt}: {e}，等待 15s...", flush=True)
            time.sleep(15)

    time.sleep(5)

print("\n================ 全部试听样音生成完成 ================", flush=True)
for name, desc, url in results:
    print(f"- 【{name}】({desc}): {url}")
