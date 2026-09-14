import json
import re
import pandas as pd
from collections import Counter
import os

def get_syllables(word):
    """
    拆解規則修正版：
    1. 轉小寫：統計時不分大小寫。
    2. 母音: a, e, i, o, u
    3. 遇到 '子音+母音' 的組合時：
       - 若當前音節buffer中已經有母音 -> 切分 (Onset)
       - 若當前音節buffer中還沒母音 -> 不切分 (視為首字子音群 Cluster)
    4. 剩餘子音歸前 (Coda)
    """
    if not word:
        return []

    # --- 修改重點：在這裡直接轉成小寫 ---
    word = word.lower()
    # --------------------------------

    # 定義母音 (因為已經轉小寫，這裡只要小寫即可)
    vowels = set('aeiou')
    
    # 切分分隔符
    raw_parts = re.split(r'[ \-]+', word)
    
    syllables = []

    for part in raw_parts:
        if not part:
            continue
        
        current_syllable = ""
        chars = list(part)
        length = len(chars)
        
        for i, char in enumerate(chars):
            is_vowel = char in vowels
            
            # 判斷是否為 "新音節的開頭 (Onset)"
            # 條件：當前是子音 AND 下一個是母音
            is_onset_pattern = (not is_vowel) and (i + 1 < length) and (chars[i+1] in vowels)
            
            # 關鍵修正：只有當「目前的音節 buffer 裡已經有母音」時，才執行切分
            has_vowel_in_buffer = any(c in vowels for c in current_syllable)
            
            if is_onset_pattern and has_vowel_in_buffer:
                # 結算上一個音節
                syllables.append(current_syllable)
                # 開啟新音節
                current_syllable = char
            else:
                current_syllable += char
        
        # 加入最後殘留的音節
        if current_syllable:
            syllables.append(current_syllable)
            
    return syllables

def main():
    # 你的檔案路徑
    input_file = r"c:\Users\jimmy\OneDrive\桌面\台灣南島與新詞專題\新詞整合\新詞譯詞\01阿美語\merged_output.json"
    output_file = r"c:\Users\jimmy\OneDrive\桌面\台灣南島與新詞專題\新詞整合\新詞譯詞\01阿美語\syllable_statistics_v2.xlsx"

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
                    # 這裡回傳的 sylls 已經全部是小寫了
                    sylls = get_syllables(fm_word)
                    all_syllables.extend(sylls)
                    
                    word_breakdown_list.append({
                        "中文詞": ch_word,
                        "族語詞": fm_word,  # 這裡保留原始大小寫，方便對照
                        "拆解結果": ", ".join(sylls), # 這裡是小寫
                        "音節數": len(sylls)
                    })

    # 1. 統計 (現在全部都是小寫統計)
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
    print(f"前 5 名高頻音節 (已轉小寫): {df_stats.head(5).values.tolist()}")

if __name__ == "__main__":
    main()
