import subprocess
import json

cmd = ['yt-dlp', '--dump-json', 'https://www.bilibili.com/video/BV1G1CXByEbX']
out = subprocess.check_output(cmd).decode('utf-8', errors='ignore')
data = json.loads(out)
chapters = data.get('chapters')
print('Chapters count:', len(chapters) if chapters else 0)
if chapters:
    for i, c in enumerate(chapters):
        print(f"{i+1}. {c.get('title')} | {c.get('start_time')}s ({c.get('start_time')//60}m{c.get('start_time')%60:.0f}s) - {c.get('end_time')}s")
else:
    print('No chapters field in metadata.')

desc = data.get('description', '')
print('\n--- Description ---')
print(desc)
