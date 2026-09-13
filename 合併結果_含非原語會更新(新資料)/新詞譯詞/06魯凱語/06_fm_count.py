import json
import re
import pandas as pd
from collections import Counter
import os

def get_syllables(word):
    """
    拆解規則 (魯凱語)：
    1. 基礎母音: a, e, i, u, o, é, ɨ, ē (會吸附前面的子音)。
    2. 獨立音節: wy, cy (永遠是母音性質，且強制切分)。
    3. 絕對子音: lr, tr, dr, dh, hw, sw (視為不可分割的單一子音)。
    4. 變色龍單位: tiy, ciy, siy, piy, kuw, huw, sew, suw
       - 若下一個是母音 -> 視為子音 (Onset)
       - 若下一個是子音/結束 -> 視為母音 (Nucleus)
       - 若連需接兩個母音 -> 在第一個母音結束 (Onset)
    """
    if not word:
        return []

    # --- 修改處：先移除所有數字 ---
    # 將所有 0-9 的數字替換為空字串
    word = re.sub(r'\d+', '', word)

    word = word.lower().strip()
    
    # 若移除數字後變為空字串，直接回傳
    if not word:
        return []
    
    # 1. 定義類別
    # 更新：加入 é, ɨ (保留 ē 以防萬一)
    basic_vowels = set('aeiuoéɨē')
    
    # 獨立音節 (永遠是母音，且排斥前方的子音)
    standalone_units = {'wy', 'cy'} 
    
    # 更新：加入 lr, tr, dh
    # 雖然邏輯上它們歸類為"非母音"，但必須列出以供 Regex 識別
    absolute_consonants = {'lr', 'tr', 'dr', 'dh'}
    
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
        
        # --- Regex 更新 ---
        # 必須包含新的絕對子音 lr, tr, dh，確保它們不被拆開
        # 順序：長字串 (3字元) -> 短字串 (2字元) -> 單字元
        pattern = r'tiy|ciy|siy|piy|kuw|huw|sew|suw|wy|cy|lr|tr|dr|dh|.'
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
                # 其他 (lr, tr, dr, dh, b, c...) 都是子音
                is_role_vowel = False
            
            # --- 步驟 C: 切分邏輯 ---
            
            should_split = False
            
            # 1. Onset 切分: 當前是子音 + 下一個是母音 + Buffer已有母音
            # 例如: ma-lra -> ma (有母音), lr (子), a (母) -> 切分 -> ma, lra
            if (not is_role_vowel) and next_is_vowel_starter and has_vowel_in_buffer:
                should_split = True
                
            # 2. 獨立音節切分 (cy, wy)
            if is_role_standalone and len(current_syllable) > 0:
                should_split = True
                
            # 3. 變色龍母音切分: 如果當前是變色龍變成的母音，且前面已經有母音
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
    input_file = r"c:\Users\jimmy\OneDrive\桌面\台灣南島與新詞專題\新詞整合\新詞譯詞\06魯凱語\merged_output.json"
    output_file = r"c:\Users\jimmy\OneDrive\桌面\台灣南島與新詞專題\新詞整合\新詞譯詞\06魯凱語\syllable_statistics_v10_no_digits.xlsx"

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
        "lra123",        # 測試數字移除 -> 預期: lra
        "tré456",        # 測試數字移除 -> 預期: tré
        "dhɨ7",          # 測試數字移除 -> 預期: dhɨ
        "huw8siyē",      # 測試中間數字 -> 預期: huw, siyē
        "sewsew"         
    ]
    print("\n--- 測試結果 ---")
    for w in test_words:
        print(f"{w} -> {get_syllables(w)}")

if __name__ == "__main__":
    main()
