import json
import re
import pandas as pd
from collections import Counter
import os

# --- 特例字典 ---
# 在這裡定義不符合通則的單字
EXCEPTIONS = {
    "tiyisu": ["ti", "yi", "su"],  # 強制指定拆解
}

def get_syllables(word):
    """
    拆解規則 v10 (特例優先 + 擴增變色龍 + 去除數字)：
    1. 前處理: 移除字串中的所有數字 (0-9)。
    2. 特例檢查: 若單字在 EXCEPTIONS 中，直接回傳指定拆解。
    3. 基礎母音: a, e, i, u, o, ē
    4. 獨立音節: wy, cy (永遠是母音性質，且強制切分)
    5. 絕對子音: dr (永遠是子音)
    6. 變色龍單位: tiy, ciy, siy, piy, kuw, huw, sew, suw
       - 若下一個是母音 -> 視為子音 (Onset)
       - 若下一個是子音/結束 -> 視為母音 (Nucleus)
    """
    if not word:
        return []

    # --- 步驟 1: 先移除所有數字 ---
    word = re.sub(r'\d+', '', word)
    word = word.lower().strip()
    
    if not word:
        return []

    # --- 步驟 2: 特例優先處理 ---
    if word in EXCEPTIONS:
        return EXCEPTIONS[word]
    
    # --- 步驟 3: 標準規則處理 ---
    
    # 定義類別
    basic_vowels = set('aeiuoē')
    standalone_units = {'wy', 'cy'} # 永遠是母音，且排斥前方的子音
    absolute_consonants = {'dr'}    # 永遠是子音
    
    # 變色龍單位
    dynamic_units = {'tiy', 'ciy', 'siy', 'piy', 'kuw', 'huw', 'sew', 'suw'} 
    
    # 切分分隔符
    raw_parts = re.split(r'[ \-]+', word)
    
    syllables = []

    for part in raw_parts:
        if not part:
            continue
        
        current_syllable = ""
        has_vowel_in_buffer = False 
        
        # Regex: 包含所有特殊單位
        pattern = r'tiy|ciy|siy|piy|kuw|huw|sew|suw|wy|cy|dr|.'
        chars = re.findall(pattern, part)
        
        length = len(chars)
        
        for i, char in enumerate(chars):
            # --- 步驟 A: 判斷下一個單位的性質 (Lookahead) ---
            next_is_vowel_starter = False
            if i + 1 < length:
                next_char = chars[i+1]
                # 只有基礎母音或獨立母音(wy, cy)才算"母音開頭"
                if next_char in basic_vowels or next_char in standalone_units:
                    next_is_vowel_starter = True
            
            # --- 步驟 B: 判斷當前單位的身分 (Role) ---
            is_role_vowel = False
            is_role_standalone = False 
            
            if char in basic_vowels:
                is_role_vowel = True
            elif char in standalone_units:
                is_role_vowel = True
                is_role_standalone = True
            elif char in dynamic_units:
                # 變色龍邏輯
                if next_is_vowel_starter:
                    is_role_vowel = False # 後面有母音，我當子音 (如 suw-a)
                else:
                    is_role_vowel = True  # 後面沒母音，我當母音 (如 ma-suw)
            else:
                # 其他 (dr, b, c...) 都是子音
                is_role_vowel = False
            
            # --- 步驟 C: 切分邏輯 ---
            
            should_split = False
            
            # 1. Onset 切分: 當前是子音 + 下一個是母音 + Buffer已有母音
            if (not is_role_vowel) and next_is_vowel_starter and has_vowel_in_buffer:
                should_split = True
                
            # 2. 獨立音節切分 (cy, wy)
            if is_role_standalone and len(current_syllable) > 0:
                should_split = True
                
            # 3. 變色龍母音切分: 如果當前是變色龍變成的母音，且前面已經有母音
            # 例如: ma-suw (ma, suw)
            if char in dynamic_units and is_role_vowel and has_vowel_in_buffer:
                should_split = True

            # --- 執行動作 ---
            if should_split:
                syllables.append(current_syllable)
                current_syllable = char
                # 重置 buffer
                if is_role_vowel:
                    has_vowel_in_buffer = True
                else:
                    has_vowel_in_buffer = False
            else:
                current_syllable += char
                if is_role_vowel:
                    has_vowel_in_buffer = True
        
        if current_syllable:
            syllables.append(current_syllable)
            
    return syllables

def main():
    # 檔案路徑
    input_file = r"c:\Users\jimmy\OneDrive\桌面\台灣南島與新詞專題\新詞整合\新詞譯詞\05卑南語\merged_output.json"
    output_file = r"c:\Users\jimmy\OneDrive\桌面\台灣南島與新詞專題\新詞整合\新詞譯詞\05卑南語\syllable_statistics_v10_exception.xlsx"

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
        "tiyisu",        # 特例測試 -> 預期: ti, yi, su
        "tiyisu123",     # 數字測試 -> 預期: ti, yi, su (數字移除後命中特例)
        "huwsiyē",       # 規則測試
        "masuwa",        # 規則測試
    ]
    print("\n--- 測試結果 ---")
    for w in test_words:
        print(f"{w} -> {get_syllables(w)}")

if __name__ == "__main__":
    main()
