import json
import re
import pandas as pd
from collections import Counter
import os

def get_syllables(word):
    """
    拆解規則 v6 (獨立音節版)：
    1. 轉小寫。
    2. 基礎母音: a, e, i, o, u (會吸附前面的子音)。
    3. 獨立音節單位: wy, cy 
       - 視為母音核心。
       - **特性**：不接受前面的子音作為 Onset (除非它是字首)。
       - 遇到它們時，前面的子音會被迫留在上一個音節。
    4. 絕對子音單位: dr, tiy, ciy, siy, piy (視為不可分割的子音)。
    """
    if not word:
        return []

    word = word.lower().strip()
    
    # 基礎母音 (會觸發 Onset 切分)
    basic_vowels = set('aeiou')
    # 獨立音節單位 (自己成一格，不吸附前方子音)
    standalone_units = {'wy', 'cy'}
    # 絕對子音單位
    consonant_units = {'dr', 'tiy', 'ciy', 'siy', 'piy'}
    
    # 切分分隔符
    raw_parts = re.split(r'[ \-]+', word)
    
    syllables = []

    for part in raw_parts:
        if not part:
            continue
        
        current_syllable = ""
        has_vowel_in_buffer = False 
        
        # Regex: 確保長字串優先匹配
        pattern = r'tiy|ciy|siy|piy|wy|cy|dr|.'
        chars = re.findall(pattern, part)
        
        length = len(chars)
        
        for i, char in enumerate(chars):
            # 1. 判斷下一個字元類型
            next_is_basic_vowel = False
            if i + 1 < length:
                next_char = chars[i+1]
                if next_char in basic_vowels:
                    next_is_basic_vowel = True
            
            # 2. 判斷當前字元類型
            is_current_basic_vowel = char in basic_vowels
            is_current_standalone = char in standalone_units
            is_current_vowel_type = is_current_basic_vowel or is_current_standalone
            
            # --- 切分邏輯核心 ---
            
            # 情況 A: 標準 Onset 切分
            # 當前是子音 + 下一個是"基礎母音" + Buffer已有母音
            # 例如: ca-n... 下一個是 a -> ca, na
            # 注意：如果下一個是 cy (standalone)，這裡會是 False，所以 n 不會被切走
            is_onset_start = (not is_current_vowel_type) and next_is_basic_vowel
            
            # 情況 B: 獨立音節切分
            # 當前就是獨立音節 (cy, wy) + Buffer不為空
            # 例如: can + cy -> can, cy
            is_standalone_start = is_current_standalone and (len(current_syllable) > 0)

            if (is_onset_start and has_vowel_in_buffer) or is_standalone_start:
                # 結算上一個音節
                syllables.append(current_syllable)
                # 開啟新音節
                current_syllable = char
                
                # 重置 buffer 狀態
                # 如果新開頭的是 cy/wy，那 buffer 已經有母音了
                # 如果新開頭的是子音 (Onset)，那 buffer 還沒母音
                if is_current_standalone:
                    has_vowel_in_buffer = True
                else:
                    has_vowel_in_buffer = False
            else:
                current_syllable += char
                if is_current_vowel_type:
                    has_vowel_in_buffer = True
        
        # 加入最後殘留的音節
        if current_syllable:
            syllables.append(current_syllable)
            
    return syllables

def main():
    # 檔案路徑 (請依需求修改)
    input_file = r"c:\Users\jimmy\OneDrive\桌面\台灣南島與新詞專題\新詞整合\新詞譯詞\04布農語\merged_output.json"
    output_file = r"c:\Users\jimmy\OneDrive\桌面\台灣南島與新詞專題\新詞整合\新詞譯詞\04布農語\syllable_statistics_v6.xlsx"

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"錯誤: 找不到檔案 {input_file}")
        return

    all_syllables = []
    word_breakdown_list = []

    for ch_word, content in data.items():
        if "new_word" in content:
            for item in content["new_word"]:
                fm_word = item.get("fm_word", "")
                if fm_word:
                    sylls = get_syllables(fm_word)
                    all_syllables.extend(sylls)
                    
                    word_breakdown_list.append({
                        "中文詞": ch_word,
                        "族語詞": fm_word, 
                        "拆解結果": ",".join(sylls), 
                        "音節數": len(sylls)
                    })

    # 1. 統計
    syllable_counts = Counter(all_syllables)
    df_stats = pd.DataFrame(syllable_counts.items(), columns=['音節', '出現次數'])
    df_stats = df_stats.sort_values(by='出現次數', ascending=False).reset_index(drop=True)

    # 2. 詳情
    df_details = pd.DataFrame(word_breakdown_list)

    # 寫入 Excel
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_stats.to_excel(writer, sheet_name='音節統計', index=False)
        df_details.to_excel(writer, sheet_name='單字拆解詳情', index=False)

    print(f"處理完成！已生成檔案: {output_file}")
    print(f"前 5 名高頻音節: {df_stats.head(5).values.tolist()}")

    # --- 測試範例 ---
    test_words = [
        "cehuycaycancy", # 預期: ce, huy, cay, can, cy
        "ciyencayen",    # 預期: ciyen, ca, yen
        "mancy",         # 預期: man, cy
        "wyvu",          # 預期: wy, vu
        "macy"           # 預期: ma, cy
    ]
    print("\n--- 測試結果 ---")
    for w in test_words:
        print(f"{w} -> {get_syllables(w)}")

if __name__ == "__main__":
    main()
