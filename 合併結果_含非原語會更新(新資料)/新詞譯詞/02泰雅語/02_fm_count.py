import json
import re
import pandas as pd
from collections import Counter
import os

def get_syllables(word):
    """
    拆解規則修正版 (v4)：
    1. 轉小寫。
    2. 特殊規則：將 'ry' 視為一個不可分割的子音單位。
    3. 母音: a, e, i, o, u
    4. Onset 優先：遇到 '子音+母音' 且 buffer 有母音時切分。
    5. Coda 歸前：剩餘子音歸前。
    """
    if not word:
        return []

    # 1. 轉小寫
    word = word.lower()
    # 2. 移除前後多餘空白
    word = word.strip()

    vowels = set('aeiou')
    
    # 切分分隔符 (以空格或連字號切開原始字串)
    raw_parts = re.split(r'[ \-]+', word)
    
    syllables = []

    for part in raw_parts:
        if not part:
            continue
        
        current_syllable = ""
        
        # --- 修改重點：使用 Regex 來建立字元清單 ---
        # 說明：r'ry|.' 的意思是「先找 ry，找到了算一個；沒找到則找任意單一字元」
        # 這樣 ['a', 'r', 'y', 'u'] 會變成 ['a', 'ry', 'u']
        chars = re.findall(r'ry|.', part)
        # ---------------------------------------
        
        length = len(chars)
        
        for i, char in enumerate(chars):
            # 判斷是否為母音 (ry 不在 vowels 集合裡，所以會被判定為子音，正確)
            is_vowel = char in vowels
            
            # 判斷是否為 "新音節的開頭 (Onset)"
            # 條件：當前是子音 AND 下一個是母音
            is_onset_pattern = (not is_vowel) and (i + 1 < length) and (chars[i+1] in vowels)
            
            # 只有當「目前的音節 buffer 裡已經有母音」時，才執行切分
            has_vowel_in_buffer = any(c in vowels for c in current_syllable)
            
            if is_onset_pattern and has_vowel_in_buffer:
                syllables.append(current_syllable)
                current_syllable = char
            else:
                current_syllable += char
        
        if current_syllable:
            syllables.append(current_syllable)
            
    return syllables

def main():
    # 檔案路徑 (請確認你的路徑是否正確)
    input_file = r"c:\Users\jimmy\OneDrive\桌面\台灣南島與新詞專題\新詞整合\新詞譯詞\02泰雅語\merged_output.json"
    output_file = r"c:\Users\jimmy\OneDrive\桌面\台灣南島與新詞專題\新詞整合\新詞譯詞\02泰雅語\syllable_statistics_v3.xlsx"

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

if __name__ == "__main__":
    main()
