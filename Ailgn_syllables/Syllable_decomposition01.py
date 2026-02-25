import json
import re
import os

def get_syllables(word):
    """
    拆解規則修正版:
    1. 找出母音 (包含擬母音 Syllabic Nasal: 前面無母音的 n/ng)。
    2. 切割規則：
       - 如果核心是擬母音 (n/ng): 強制在該 n/ng 結束處切斷 (視為音節結尾)。
       - 如果核心是標準母音: 
         (a) 優先檢查後方是否有 n/ng 作為 Coda。
         (b) 否則採用一般規則 (保留子音給下個音節)。
    """
    if not word:
        return []

    word = word.lower()
    vowels = set('aeiouʉéɨyw')
    raw_parts = re.split(r'[ \-]+', word)
    all_syllables = []

    for part in raw_parts:
        if not part: continue
        
        v_indices = []
        skip_next = False 

        for i, char in enumerate(part):
            if skip_next:
                skip_next = False
                continue
            if char in vowels:
                v_indices.append(i)
                continue
            if part[i:i+2] == 'ng':
                is_preceded_by_vowel = (i > 0 and part[i-1] in vowels)
                if not is_preceded_by_vowel:
                    v_indices.append(i)
                skip_next = True 
                continue
            if char == 'n':
                is_preceded_by_vowel = (i > 0 and part[i-1] in vowels)
                if not is_preceded_by_vowel:
                    v_indices.append(i)
                continue

        if not v_indices:
            all_syllables.append(part)
            continue
            
        start_idx = 0
        for i, current_v_idx in enumerate(v_indices):
            end_idx = len(part)
            is_syllabic = part[current_v_idx] not in vowels
            
            if is_syllabic:
                if part[current_v_idx:current_v_idx+2] == 'ng':
                    end_idx = current_v_idx + 2
                else:
                    end_idx = current_v_idx + 1
            elif i + 1 < len(v_indices):
                next_v_idx = v_indices[i+1]
                if (current_v_idx + 2 < len(part)) and \
                   (part[current_v_idx+1 : current_v_idx+3] == 'ng') and \
                   (current_v_idx + 3 <= next_v_idx):
                    end_idx = current_v_idx + 3
                elif (current_v_idx + 1 < len(part)) and \
                     (part[current_v_idx+1] == 'n') and \
                     (current_v_idx + 2 <= next_v_idx):
                    end_idx = current_v_idx + 2
                else:
                    cut_candidate = next_v_idx - 1
                    if cut_candidate in v_indices or part[cut_candidate] in vowels:
                        end_idx = next_v_idx
                    else:
                        end_idx = cut_candidate
            
            if end_idx < start_idx:
                end_idx = start_idx

            syllable = part[start_idx:end_idx]
            if syllable:
                all_syllables.append(syllable)
            start_idx = end_idx
            
        if start_idx < len(part):
            remainder = part[start_idx:]
            if all_syllables:
                all_syllables[-1] += remainder
            else:
                all_syllables.append(remainder)

    return all_syllables

def process_data_payload(data):
    """
    直接處理 Python Dictionary 資料，回傳處理後的 List
    """
    output_data = []
    
    # 針對原始資料格式遍歷
    for ch_word, content in data.items():
        if "new_word" in content:
            for item in content["new_word"]:
                fm_word = item.get("fm_word", "")
                ch_semantic = item.get("ch_semantic", "")
                if fm_word:
                    # 取得音節列表 (全小寫)
                    sylls = get_syllables(fm_word)
                    
                    # 建立單字資料物件
                    word_entry = {
                        "chinese_word": ch_word,
                        "amis_word": fm_word,       # 保留原始大小寫
                        "ch_semantic": ch_semantic,
                        "syllables": sylls,         # 音節陣列
                        "syllable_count": len(sylls)
                    }
                    output_data.append(word_entry)
    return output_data

def model_main(input_file):
    """保留舊接口以防單獨呼叫"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"錯誤: 找不到檔案 {input_file}")
        return "[]"

    result_list = process_data_payload(data)
    return json.dumps(result_list, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    # 測試用
    pass
