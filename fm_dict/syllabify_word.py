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
    回傳格式: "jaq-u"
    """
    if not VOWEL_PATTERN.search(word):
        return word
    
    vowel_matches = list(VOWEL_PATTERN.finditer(word))
    
    if len(vowel_matches) <= 1:
        return word

    syllables = []
    start_idx = 0
    
    for i in range(len(vowel_matches)):
        current_vowel = vowel_matches[i]
        v_start = current_vowel.start()
        
        if i == 0:
            pass
        else:
            prev_vowel = vowel_matches[i-1]
            prev_v_end = prev_vowel.end()
            middle_segment = word[prev_v_end : v_start]
            
            onset_len = 0
            if len(middle_segment) == 0:
                onset_len = 0
            else:
                if middle_segment.lower().endswith("ng"):
                    onset_len = 0 
                else:
                    onset_len = 1
            
            cut_point = v_start - onset_len
            syllables.append(word[start_idx : cut_point])
            start_idx = cut_point
            
    syllables.append(word[start_idx:])
    return "-".join(syllables)

def split_initial_final(syllable):
    """
    將單一音節拆解為聲母與韻母
    範例: "jaq" -> ("j", "aq")
    """
    match = VOWEL_PATTERN.search(syllable)
    if not match:
        return "", syllable
    
    v_start = match.start()
    initial = syllable[:v_start]
    final = syllable[v_start:]
    
    return initial, final

# ===========================
# 2. 檔案處理邏輯
# ===========================

file_mapping = {
    "01_ilrdf_dict_Amis.json": "01_阿美語",
    "02_ilrdf_dict_Atayal.json": "02_泰雅語",
    "03_ilrdf_dict_Paiwan.json": "03_排灣語",
    "04_ilrdf_dict_Bunun.json": "04_布農語",
    "05_ilrdf_dict_Puyuma.json": "05_卑南語",
    "06_ilrdf_dict_Rukai.json": "06_魯凱語",
    "07_ilrdf_dict_Tsou.json": "07_鄒語",
    "08_ilrdf_dict_SaySiyat.json": "08_賽夏語",
    "09_ilrdf_dict_Tao.json": "09_雅美語",
    "10_ilrdf_dict_Thao.json": "10_邵語",
    "11_ilrdf_dict_Kavalan.json": "11_噶瑪蘭語",
    "12_ilrdf_dict_Truku.json": "12_太魯閣語",
    "13_ilrdf_dict_Sakizaya.json": "13_撒奇萊雅語",
    "14_ilrdf_dict_Seediq.json": "14_賽德克語",
    "15_ilrdf_dict_Hla'alua.json": "15_拉阿魯哇語",
    "16_ilrdf_dict_Kanakanavu.json": "16_卡那卡那富語"
}

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
                
                cut_result_dict = {}
                
                # 準備 4 個計數器
                syllable_counter = Counter()        # 1. 完整音節
                initial_counter = Counter()         # 2. 聲母
                final_counter = Counter()           # 3. 韻母
                merged_components_counter = Counter() # 4. 聲韻母合併
                
                for key in data.keys():
                    sub_words = key.split(' ')
                    processed_sub_words = []
                    
                    for w in sub_words:
                        cut_word = syllabify_word(w)
                        processed_sub_words.append(cut_word)
                        
                        syllables = cut_word.split('-')
                        for s in syllables:
                            s = s.strip()
                            if s:
                                # 1. 統計完整音節
                                syllable_counter[s] += 1
                                
                                # 拆解聲韻母
                                ini, fin = split_initial_final(s)
                                
                                # 2. 統計聲母
                                if ini: 
                                    initial_counter[ini] += 1
                                    # 4. 加入合併統計
                                    merged_components_counter[ini] += 1
                                    
                                # 3. 統計韻母
                                if fin: 
                                    final_counter[fin] += 1
                                    # 4. 加入合併統計
                                    merged_components_counter[fin] += 1
                    
                    processed_key = ' '.join(processed_sub_words)
                    cut_result_dict[key] = processed_key
                
                # --- 輸出 0: 切割結果 JSON (原始功能) ---
                cut_filename = f"{base_name}_音節切割.json"
                with open(os.path.join(output_cut_folder, cut_filename), 'w', encoding='utf-8') as out_f:
                    json.dump(cut_result_dict, out_f, ensure_ascii=False, indent=2)
                
                # --- 輸出 1: 完整音節統計 ---
                syl_stat_filename = f"{base_name}_音節統計.json"
                sorted_syl = dict(syllable_counter.most_common())
                with open(os.path.join(output_stat_folder, syl_stat_filename), 'w', encoding='utf-8') as out_f:
                    json.dump(sorted_syl, out_f, ensure_ascii=False, indent=2)

                # --- 輸出 2: 聲母統計 ---
                ini_stat_filename = f"{base_name}_聲母統計.json"
                sorted_ini = dict(initial_counter.most_common())
                with open(os.path.join(output_stat_folder, ini_stat_filename), 'w', encoding='utf-8') as out_f:
                    json.dump(sorted_ini, out_f, ensure_ascii=False, indent=2)

                # --- 輸出 3: 韻母統計 ---
                fin_stat_filename = f"{base_name}_韻母統計.json"
                sorted_fin = dict(final_counter.most_common())
                with open(os.path.join(output_stat_folder, fin_stat_filename), 'w', encoding='utf-8') as out_f:
                    json.dump(sorted_fin, out_f, ensure_ascii=False, indent=2)

                # --- 輸出 4: 聲韻母合併統計 ---
                merged_stat_filename = f"{base_name}_聲韻母合併統計.json"
                sorted_merged = dict(merged_components_counter.most_common())
                with open(os.path.join(output_stat_folder, merged_stat_filename), 'w', encoding='utf-8') as out_f:
                    json.dump(sorted_merged, out_f, ensure_ascii=False, indent=2)
                
                processed_count += 1
                
            except json.JSONDecodeError:
                print(f"❌ 格式錯誤 (JSON Decode Error): {input_file}")
    else:
        print(f"⚠️ 找不到檔案: {input_file}")

print("="*30)
print(f"處理完成！共處理 {processed_count} 個檔案。")
print(f"所有統計結果已存入: {output_stat_folder}")
