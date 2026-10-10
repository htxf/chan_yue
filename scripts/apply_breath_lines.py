import os
import json
import re

def get_line_text(line):
    return ''.join(c.get('text', '') for c in line.get('chars', [])).strip()

def get_clean_han_count(text):
    return len([c for c in text if '\u4e00' <= c <= '\u9fff'])

def detect_verse_paragraph(lines):
    if len(lines) < 4:
        return False
    lengths = [get_clean_han_count(get_line_text(l)) for l in lines]
    if all(l in (4, 5, 7) for l in lengths) and len(set(lengths)) == 1:
        return True
    return False

def split_long_line_by_breath(line):
    chars = line.get('chars', [])
    text = ''.join(c.get('text', '') for c in chars)
    han_count = get_clean_han_count(text)
    
    # 22 字以内的自然呼吸句不拆分
    if han_count <= 22:
        return [line]
        
    # 如果超过 22 字，寻找最自然的意群停顿点（逗号、冒号、分号）
    split_indices = []
    accum = 0
    for idx, c in enumerate(chars):
        t = c.get('text', '')
        if '\u4e00' <= t <= '\u9fff':
            accum += 1
        if t in ('，', '：', '；') and accum >= 10:
            remain_han = han_count - accum
            if remain_han >= 8:
                split_indices.append(idx + 1)
                accum = 0
                
    if not split_indices:
        return [line]
        
    res = []
    start_idx = 0
    for s_idx in split_indices:
        sub_chars = chars[start_idx:s_idx]
        first_char = next((c for c in sub_chars if 'startTime' in c), None)
        last_char = next((c for c in reversed(sub_chars) if 'endTime' in c), None)
        res.append({
            'lineStart': first_char['startTime'] if (first_char and 'startTime' in first_char) else line['lineStart'],
            'lineEnd': last_char['endTime'] if (last_char and 'endTime' in last_char) else line['lineEnd'],
            'chars': sub_chars
        })
        start_idx = s_idx
        
    if start_idx < len(chars):
        sub_chars = chars[start_idx:]
        first_char = next((c for c in sub_chars if 'startTime' in c), None)
        last_char = next((c for c in reversed(sub_chars) if 'endTime' in c), None)
        res.append({
            'lineStart': first_char['startTime'] if (first_char and 'startTime' in first_char) else line['lineStart'],
            'lineEnd': last_char['endTime'] if (last_char and 'endTime' in last_char) else line['lineEnd'],
            'chars': sub_chars
        })
    return res

def process_book(book_dir, dry_run=True):
    p = os.path.join('src', 'data', book_dir)
    files = [f for f in os.listdir(p) if f.startswith('chapter_')]
    files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
    
    total_before = 0
    total_after = 0
    
    print(f"\n=================== BREATH-LINE TUNING: {book_dir.upper()} (DryRun={dry_run}) ===================")
    for f in files:
        file_path = os.path.join(p, f)
        data = json.load(open(file_path, 'r', encoding='utf-8'))
        ch_before = 0
        ch_after = 0
        
        for para in data.get('paragraphs', []):
            orig_lines = para.get('lines', [])
            is_verse = detect_verse_paragraph(orig_lines)
            
            orig_chars_text = ''.join(''.join(c.get('text', '') for c in l.get('chars', [])) for l in orig_lines)
            
            refined_lines = []
            if is_verse:
                refined_lines = orig_lines
            else:
                for l in orig_lines:
                    refined_lines.extend(split_long_line_by_breath(l))
                    
            refined_chars_text = ''.join(''.join(c.get('text', '') for c in l.get('chars', [])) for l in refined_lines)
            
            # 校验 1：字符绝对 1:1 无损
            assert orig_chars_text == refined_chars_text, f"Mismatch in {f} para! {len(orig_chars_text)} vs {len(refined_chars_text)}"
            
            # 校验 2：时间轴单调
            prev_start = -1
            for rl in refined_lines:
                s = rl['lineStart']
                e = rl['lineEnd']
                assert s <= e, f"Timeline inverted in {f}: {s} > {e}"
                assert s >= prev_start, f"Timeline non-monotonic in {f}: {s} < {prev_start}"
                prev_start = s
                
            ch_before += len(orig_lines)
            ch_after += len(refined_lines)
            para['lines'] = refined_lines
            
        total_before += ch_before
        total_after += ch_after
        
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as out_f:
                json.dump(data, out_f, ensure_ascii=False, indent=2)
                
    print(f"[{book_dir}] Lines: {total_before} -> {total_after} (调整长句比例为优雅呼吸行)")

if __name__ == '__main__':
    import sys
    dry_run = '--apply' not in sys.argv
    process_book('jingangjing', dry_run=dry_run)
    process_book('dizangjing', dry_run=dry_run)
    process_book('xinjing', dry_run=dry_run)
