import os
import json
import re

SENTENCE_ENDERS = {'。', '？', '；', '”', '」', '』'}

def get_line_text(line):
    return ''.join(c.get('text', '') for c in line.get('chars', [])).strip()

def get_clean_han_count(line):
    txt = get_line_text(line)
    return len([c for c in txt if '\u4e00' <= c <= '\u9fff'])

def is_vocative_or_short_opener(txt):
    """判断是否为呼格、短叹词或引语前缀（绝不应独立成行）"""
    # 如：“希有，”、“世尊！”、“善哉！”、“须菩提！”、“文殊师利！”、“地藏！”
    if len(txt) <= 5 and txt[-1] in ('！', '，', '：'):
        return True
    if txt in ('“希有，', '“善哉，', '善哉！', '“唯然，', '文殊师利！', '地藏！', '须菩提！', 
               '世尊！', '「世尊！', '「地藏！', '「四天王！', '「普广！', '佛告普广：', '佛言：'):
        return True
    return False

def detect_verse_paragraph(lines):
    """检测是否为整齐的诗偈段落（如4行以上且字数高度一致，如四言、五言、七言）"""
    if len(lines) < 4:
        return False
    lengths = [get_clean_han_count(l) for l in lines]
    if all(l in (4, 5, 7) for l in lengths) and len(set(lengths)) == 1:
        return True
    return False

def merge_paragraph_lines(lines, is_verse=False):
    if not lines or is_verse:
        return lines

    merged = []
    current_acc = []

    def flush():
        nonlocal current_acc
        if not current_acc:
            return
        first_line = current_acc[0]
        last_line = current_acc[-1]
        
        combined_chars = []
        for l in current_acc:
            combined_chars.extend(l.get('chars', []))
            
        merged_line = {
            'lineStart': first_line.get('lineStart', 0),
            'lineEnd': last_line.get('lineEnd', 0),
            'chars': combined_chars
        }
        merged.append(merged_line)
        current_acc = []

    for i, line in enumerate(lines):
        txt = get_line_text(line)
        if not txt:
            continue
            
        current_acc.append(line)
        last_char = txt[-1] if txt else ''
        acc_text = ''.join(get_line_text(l) for l in current_acc)
        acc_han = len([c for c in acc_text if '\u4e00' <= c <= '\u9fff'])
        
        # 1. 呼格/短引语绝不断开
        if is_vocative_or_short_opener(txt):
            continue
            
        # 2. 逗号/顿号是句中分句，非句子终结；字数未超过预算(45字)时向后合并
        if last_char in ('，', '、'):
            if acc_han >= 45:
                flush()
            continue
            
        # 3. 冒号引语（如“合掌恭敬而白佛言：”）字数达到一定程度可断开，否则吸纳后文
        if last_char == '：':
            if acc_han >= 16:
                flush()
            continue
            
        # 4. 遇到句子终结符 (。 ？ ； 闭引号)
        if last_char in SENTENCE_ENDERS:
            # 极短对称问句微合并（例如“生何世界？生何天中？”）
            if acc_han <= 5 and i + 1 < len(lines):
                next_txt = get_line_text(lines[i+1])
                if len(next_txt) <= 5 and next_txt[-1] in ('？', '。'):
                    continue
            flush()
            continue
            
        # 5. 感叹号
        if last_char == '！':
            if acc_han > 4:
                flush()
            continue

    flush()
    return merged

def process_book(book_dir, dry_run=True):
    p = os.path.join('src', 'data', book_dir)
    files = [f for f in os.listdir(p) if f.startswith('chapter_')]
    files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
    
    total_before = 0
    total_after = 0
    
    print(f"\n=================== PROCESSING {book_dir.upper()} (DryRun={dry_run}) ===================")
    for f in files:
        file_path = os.path.join(p, f)
        data = json.load(open(file_path, 'r', encoding='utf-8'))
        ch_before = 0
        ch_after = 0
        
        for para in data.get('paragraphs', []):
            orig_lines = para.get('lines', [])
            orig_chars_text = ''.join(''.join(c.get('text', '') for c in l.get('chars', [])) for l in orig_lines)
            
            is_verse = detect_verse_paragraph(orig_lines)
            merged = merge_paragraph_lines(orig_lines, is_verse)
            
            merged_chars_text = ''.join(''.join(c.get('text', '') for c in l.get('chars', [])) for l in merged)
            
            # 铁律校验 1：字符内容绝对 1:1 无损一致
            assert orig_chars_text == merged_chars_text, f"Text mismatch in {f}! Orig len: {len(orig_chars_text)}, Merged len: {len(merged_chars_text)}"
            
            # 铁律校验 2：时间轴单调递增与边界合法
            prev_start = -1
            for ml in merged:
                s = ml['lineStart']
                e = ml['lineEnd']
                assert s <= e, f"Timeline inverted in {f}: start {s} > end {e}"
                assert s >= prev_start, f"Timeline non-monotonic in {f}: {s} < {prev_start}"
                prev_start = s
                
            ch_before += len(orig_lines)
            ch_after += len(merged)
            para['lines'] = merged
            
        total_before += ch_before
        total_after += ch_after
        
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as out_f:
                json.dump(data, out_f, ensure_ascii=False, indent=2)
                
    print(f"[{book_dir}] Total lines: {total_before} -> {total_after} (减少 {(total_before-total_after)/total_before*100:.1f}%)")

if __name__ == '__main__':
    import sys
    dry_run = '--apply' not in sys.argv
    process_book('jingangjing', dry_run=dry_run)
    process_book('dizangjing', dry_run=dry_run)
    process_book('xinjing', dry_run=dry_run)

