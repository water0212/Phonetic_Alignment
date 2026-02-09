import json
import re
import os
from collections import Counter

def get_syllables(word):
    """
    拆解規則修正版 (User Request):
    邏輯：
    1. 找出母音。
    2. 每個音節包含：該母音前的子音(若有) + 母音本身 + 母音後的子音(Coda)。
    3. Coda 的邊界判定：直到「下一個母音的前一個子音」之前。
       (意即：下一個母音會盡量帶走它前面的一個子音當作 Onset，剩下的給前面)
    """
    if not word:
        return []

    word = word.lower()
    
    # 定義母音
    vowels = set('aeiouʉéɨy')
    
    # 先依照空格或連字號切分 (處理片語)
    raw_parts = re.split(r'[ \\-]+', word)
    
    all_syllables = []

    for part in raw_parts:
        if not part:
            continue
        
        # 1. 找出該單字中所有母音的索引位置
        v_indices = [i for i, char in enumerate(part) if char in vowels]
        
        # 如果沒有母音，則整個字視為一個音節 (或依需求處理)
        if not v_indices:
            all_syllables.append(part)
            continue
            
        start_idx = 0
        
        # 2. 遍歷每個母音來決定音節邊界
        for i, current_v_idx in enumerate(v_indices):
            # 預設切割點為字串結尾 (針對最後一個音節)
            end_idx = len(part)
            
            # 如果還有下一個母音，我們需要計算切割點
            if i + 1 < len(v_indices):
                next_v_idx = v_indices[i+1]
                
                # 邏輯：切在 "下一個母音" 的 "前一個子音" 之前
                # 也就是 next_v_idx - 1 的位置
                cut_candidate = next_v_idx - 1
                
                # 特殊情況檢查：
                # 如果 next_v_idx - 1 剛好就是當前的母音 (例如 'ia' 相連)，
                # 或者 cut_candidate 小於等於 start_idx (雖然不太可能發生)，
                # 則直接切在兩個母音中間
                if part[cut_candidate] in vowels:
                    end_idx = next_v_idx
                else:
                    # 正常情況：保留一個子音給下一個母音，剩下的歸這裡
                    end_idx = cut_candidate
            
            # 3. 提取音節
            syllable = part[start_idx:end_idx]
            if syllable:
                all_syllables.append(syllable)
            
            # 更新下一個音節的起始點
            start_idx = end_idx
            
    return all_syllables

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

        final_output = output_data

        # 寫入 JSON 檔案
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(final_output, f, ensure_ascii=False, indent=4)
            
            print(f"處理完成！已生成 JSON 檔案: {output_file}")
            print(f"共處理了 {len(output_data)} 個單字。")
            
        except Exception as e:
            print(f"寫入檔案時發生錯誤: {e}")

if __name__ == "__main__":
    main()
