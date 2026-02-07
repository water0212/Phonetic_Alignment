import json
import re
import os
from collections import Counter

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

def model_main(input_file):
    # 檢查輸入檔是否存在
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"錯誤: 找不到檔案 {input_file}")
        return

    # 準備用來輸出的列表
    output_data = []
    
    # 用來統計頻率 (如果需要的話)
    all_syllables = []

    for ch_word, content in data.items():
        if "new_word" in content:
            for item in content["new_word"]:
                fm_word = item.get("fm_word", "")
                ch_semantic = item.get("ch_semantic", "")
                if fm_word:
                    # 取得音節列表 (全小寫)
                    sylls = get_syllables(fm_word)
                    all_syllables.extend(sylls)
                    
                    # 建立單字資料物件
                    word_entry = {
                        "chinese_word": ch_word,
                        "amis_word": fm_word,       # 保留原始大小寫
                        "ch_semantic": ch_semantic,
                        "syllables": sylls,         # 音節陣列 ["syl", "la", "ble"]
                        "syllable_count": len(sylls)
                    }
                    output_data.append(word_entry)

    
    json_str = json.dumps(output_data, ensure_ascii=False, indent=4)
    # print(f"處理完成！分解音節")
    return json_str
    

def main():
    tribes = ["阿美語","泰雅語","排灣語","布農語","卑南語","魯凱語","鄒語",
       "賽夏語","雅美語","邵語","噶瑪蘭語","太魯閣語","撒奇萊雅語","賽德克語","拉阿魯哇語","卡那卡那富語",]
    base_path = os.path.dirname(os.path.abspath(__file__))
    for tribe in tribes:
        print(f"處理族語: {tribe} ...")
        input_file = os.path.join(base_path, f"{tribes.index(tribe)+1:02d}{tribe}\\merged_output.json")
        output_file = os.path.join(base_path, f"{tribes.index(tribe)+1:02d}{tribe}\\音節拆解.json")

        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"錯誤: 找不到檔案 {input_file}")
            return

        # 準備用來輸出的列表
        output_data = []
        
        # 用來統計頻率 (如果需要的話)
        all_syllables = []

        for ch_word, content in data.items():
            if "new_word" in content:
                for item in content["new_word"]:
                    fm_word = item.get("fm_word", "")
                    ch_semantic = item.get("ch_semantic", "")
                    if fm_word:
                        # 取得音節列表 (全小寫)
                        sylls = get_syllables(fm_word)
                        all_syllables.extend(sylls)
                        
                        # 建立單字資料物件
                        word_entry = {
                            "chinese_word": ch_word,
                            "amis_word": fm_word,       # 保留原始大小寫
                            "ch_semantic": ch_semantic,
                            "syllables": sylls,         # 音節陣列 ["syl", "la", "ble"]
                            "syllable_count": len(sylls)
                        }
                        output_data.append(word_entry)

        # (選用) 如果你希望 JSON 裡也包含統計資訊，可以取消下面註解並調整結構
        # syllable_counts = dict(Counter(all_syllables).most_common())
        # final_output = {
        #     "statistics": syllable_counts,
        #     "details": output_data
        # }
        
        # 這裡預設直接輸出「單字拆解詳情」的列表
        final_output = output_data

        # 寫入 JSON 檔案
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # ensure_ascii=False 確保中文正常顯示
                # indent=4 確保格式縮排美觀
                json.dump(final_output, f, ensure_ascii=False, indent=4)
            
            print(f"處理完成！已生成 JSON 檔案: {output_file}")
            print(f"共處理了 {len(output_data)} 個單字。")
            
            # 簡單印出前幾個範例確認
            if output_data:
                print("範例資料:", output_data[0])
                
        except Exception as e:
            print(f"寫入檔案時發生錯誤: {e}")

if __name__ == "__main__":
    main()
