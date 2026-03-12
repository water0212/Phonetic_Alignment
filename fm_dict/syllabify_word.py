import json
import re
import os
from collections import Counter

# ===========================
# 1. 設定與規則
# ===========================

# 定義母音 (包含特殊符號)
VOWELS = "aeiouʉéɨ"
# 建立正則表達式，不區分大小寫
VOWEL_PATTERN = re.compile(f"[{VOWELS}]", re.IGNORECASE)

def syllabify_word(word):
    """
    對單一單字進行音節切割
    規則：
    1. 母音為核心
    2. 母音前取 1 個聲母 (Onset)
    3. 剩餘輔音歸前一音節當韻尾 (Coda)
    4. ng 視為一個單元
    """
    # 如果沒有母音，直接返回原詞
    if not VOWEL_PATTERN.search(word):
        return word
    
    # 找出所有母音的位置
    vowel_matches = list(VOWEL_PATTERN.finditer(word))
    
    # 只有一個母音，不需切割
    if len(vowel_matches) <= 1:
        return word

    syllables = []
    start_idx = 0
    
    for i in range(len(vowel_matches)):
        current_vowel = vowel_matches[i]
        v_start = current_vowel.start()
        
        if i == 0:
            # 第一個母音前的部分暫時保留，等待下一個循環或結束時處理
            pass
        else:
            # 取得兩個母音中間的輔音片段
            prev_vowel = vowel_matches[i-1]
            prev_v_end = prev_vowel.end()
            middle_segment = word[prev_v_end : v_start]
            
            onset_len = 0
            
            if len(middle_segment) == 0:
                # 兩個母音相連 (VV)，直接切開
                onset_len = 0
            else:
                # 判斷聲母長度
                # 優先檢查是否以 ng 結尾 (視為一個聲母單元)
                if middle_segment.lower().endswith("ng"):
                    onset_len = 2
                else:
                    # 一般情況取最後一個字元當聲母
                    onset_len = 1
            
            # 計算切割點：母音位置 - 聲母長度
            cut_point = v_start - onset_len
            
            # 將這一段加入音節列表
            syllables.append(word[start_idx : cut_point])
            
            # 更新下一次的起始點
            start_idx = cut_point
            
    # 加入最後一段 (最後一個母音及其後方所有內容)
    syllables.append(word[start_idx:])
    
    return "-".join(syllables)

# ===========================
# 2. 檔案處理邏輯
# ===========================

# 檔案名稱對照表
file_mapping = {
    "ilrdf_dict_Amis.json": "01_阿美語",
    "ilrdf_dict_Atayal.json": "02_泰雅語",
    "ilrdf_dict_Paiwan.json": "03_排灣語",
    "ilrdf_dict_Bunun.json": "04_布農語",
    "ilrdf_dict_Puyuma.json": "05_卑南語",
    "ilrdf_dict_Rukai.json": "06_魯凱語",
    "ilrdf_dict_Tsou.json": "07_鄒語",
    "ilrdf_dict_SaySiyat.json": "08_賽夏語",
    "ilrdf_dict_Tao.json": "09_雅美語",
    "ilrdf_dict_Thao.json": "10_邵語",
    "ilrdf_dict_Kavalan.json": "11_噶瑪蘭語",
    "ilrdf_dict_Truku.json": "12_太魯閣語",
    "ilrdf_dict_Sakizaya.json": "13_撒奇萊雅語",
    "ilrdf_dict_Seediq.json": "14_賽德克語",
    "ilrdf_dict_Hla'alua.json": "15_拉阿魯哇語",
    "ilrdf_dict_Kanakanavu.json": "16_卡那卡那富語"
}

# 設定輸出資料夾
current_dir = os.path.dirname(os.path.abspath(__file__))
output_cut_folder = os.path.join(current_dir, "音節切割結果")
output_stat_folder = os.path.join(current_dir, "音節統計結果")

if not os.path.exists(output_cut_folder):
    os.makedirs(output_cut_folder)
if not os.path.exists(output_stat_folder):
    os.makedirs(output_stat_folder)

print(f"正在讀取檔案... (目錄: {current_dir})")

processed_count = 0

for input_file, base_name in file_mapping.items():
    input_path = os.path.join(current_dir, input_file)
    
    if os.path.exists(input_path):
        print(f"正在處理: {base_name} ({input_file})...")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                
                # 存放切割後的單字 (Key: 原字, Value: 切割後)
                cut_result_dict = {}
                # 存放音節統計 (Key: 音節, Value: 次數)
                syllable_counter = Counter()
                
                for key in data.keys():
                    # 處理可能包含空格的片語 (如 "a manay")
                    sub_words = key.split(' ')
                    processed_sub_words = []
                    
                    for w in sub_words:
                        # 1. 切割單字
                        cut_word = syllabify_word(w)
                        processed_sub_words.append(cut_word)
                        
                        # 2. 統計音節 (將切割後的字串用 "-" 拆開並統計)
                        # 例如 "po-den" -> ["po", "den"]
                        syllables = cut_word.split('-')
                        for s in syllables:
                            if s.strip(): # 排除空字串
                                syllable_counter[s.strip()] += 1
                    
                    # 組回片語字串
                    processed_key = ' '.join(processed_sub_words)
                    cut_result_dict[key] = processed_key
                
                # --- 輸出 1: 切割結果 JSON ---
                cut_filename = f"{base_name}_音節切割.json"
                with open(os.path.join(output_cut_folder, cut_filename), 'w', encoding='utf-8') as out_f:
                    json.dump(cut_result_dict, out_f, ensure_ascii=False, indent=2)
                
                # --- 輸出 2: 統計結果 JSON (依次數排序) ---
                stat_filename = f"{base_name}_音節統計.json"
                # 將 Counter 轉為 list 並排序 [(音節, 次數), ...]
                sorted_stats = dict(syllable_counter.most_common())
                
                with open(os.path.join(output_stat_folder, stat_filename), 'w', encoding='utf-8') as out_f:
                    json.dump(sorted_stats, out_f, ensure_ascii=False, indent=2)
                
                processed_count += 1
                
            except json.JSONDecodeError:
                print(f"❌ 格式錯誤 (JSON Decode Error): {input_file}")
    else:
        print(f"⚠️ 找不到檔案: {input_file}")

print("="*30)
print(f"處理完成！共處理 {processed_count} 個檔案。")
print(f"切割結果已存入: {output_cut_folder}")
print(f"統計結果已存入: {output_stat_folder}")
