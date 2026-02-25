import os
import json
import Syllable_decomposition01
import Syllable_dictionary02

# 路徑設定
current_dir = os.path.dirname(os.path.abspath(__file__))
INPUT_FOLDER_NAME = "16族_中借詞_清洗版"
OUTPUT_FOLDER_NAME = "Aligned_Results" # 輸出資料夾名稱
DICT_FILENAME = "cedict_normalized.json"

class PhoneticAligner:
    def __init__(self):
        self.consonant_chinese_groups = [
            {'b', 'p'}, {'m'}, {'f'}, {'d', 't'}, {'n'}, {'l', 'r'},
            {'g', 'k'}, {'d', 'j', 'z'}, {'h'}, {'j'}, {'x'},
            {'t','q','c'}, {'z', 'c', 's', 'zh', 'ch', 'sh'},
            {'d', 'j', 'z', 't', 'q', 'c'}, {'f'}
        ]
        self.consonant_tsou_groups = [
            {'b', 'p'}, {'m'}, {'f'}, {'d', 't'}, {'n'}, {'l', 'r'},
            {'g', 'k', 'q', '’', '^'}, {'d', 'j', 'z'}, {'h'}, {'j'}, {'x'},
            {'t','c'}, {'z', 'c', 's'}, {'d', 'j', 'z', 't', 'c'},
            {'f','v', 'b'}
        ]
        self.vowel_map = {'w': 'u', 'y': 'i'}

    def calculate_consonant_score(self, c_ch, c_ts):
        if not c_ch and not c_ts: return 1
        if not c_ch or not c_ts: return 0
        
        max_score = 0
        for group_ch, group_ts in zip(self.consonant_chinese_groups, self.consonant_tsou_groups):
            if c_ch in group_ch and c_ts in group_ts:
                current_score = 1 if c_ch == c_ts else 0.8
                max_score = max(max_score, current_score)
        return max_score

    def dice_coefficient(self, s1, s2):
        def normalize(s): return "".join(self.vowel_map.get(c, c) for c in s.lower())
        n1, n2 = normalize(s1), normalize(s2)
        len1, len2 = len(n1), len(n2)
        
        if len1 == 0 or len2 == 0: return 0.0

        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if n1[i - 1] == n2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        intersection = dp[len1][len2]
        return 2.0 * intersection / (len1 + len2)

    def calculate_similarity(self, syl_ch, syl_in):
        score_onset = self.calculate_consonant_score(syl_ch['onset'], syl_in['onset'])
        dice = self.dice_coefficient(syl_ch['rhyme'], syl_in['rhyme'])
        return score_onset + dice

def find_word_in_dict(word, dictionary, pinyin_info, aligner):
    """在字典中尋找單詞，返回其拼音列表 (傳入 aligner 實例以節省開銷)"""
    pinyin = [None] * len(word)
    cnt = 0
    for entry in dictionary:
        key = entry.get("traditional", "")
        if key in word:
            cnt += 1
            entry_pinyin = entry.get('pronunciations', [])
            best_sum = -100
            best_p_str = ""
            
            # 遍歷該字典詞條的所有發音組合
            for p in entry_pinyin:
                initial = p.get('initial', '')
                final = p.get('final', '')
                
                # 與輸入的族語拼音結構進行比對
                for info in pinyin_info:
                    ini, fin = info.split(",") if "," in info else ("", "")
                    sim = aligner.calculate_similarity(
                        {'onset': initial, 'rhyme': final}, 
                        {'onset': ini, 'rhyme': fin}
                    )
                    if sim > best_sum:
                        best_sum = sim
                        best_p_str = initial + "," + final
            
            # 將找到的最佳拼音填入對應位置
            try:
                idx = word.index(key)
                pinyin[idx] = best_p_str
            except ValueError:
                pass # Should not happen if key in word

        if cnt >= len(word) + 1:
            break
    
    return pinyin

def process_alignment_payload(data_list, dictionary):
    """
    接收 List[Dict] (來自 dictionary02 的輸出)，
    進行拼音對齊計算
    """
    aligner = PhoneticAligner()
    result = []
    
    for item in data_list:
        word = item.get("chinese_word", "")
        ch_semantic = item.get("ch_semantic", "")
        syllable_structure = item.get("syllable_structure", [])
        
        pinyin_info = []
        for syl in syllable_structure:
            pinyin_info.append(syl.get("split_display", ""))
            
        pinyin_ch = find_word_in_dict(word, dictionary, pinyin_info, aligner)
        
        result.append({
            "chinese": word,
            "ch_semantic": ch_semantic,
            "pinyin_info": pinyin_info,
            "dict_pinyin": pinyin_ch
        })
    return result

def main():
    # 1. 設定路徑
    input_dir = os.path.join(current_dir, INPUT_FOLDER_NAME)
    output_dir = os.path.join(current_dir, OUTPUT_FOLDER_NAME)
    dict_path = os.path.join(current_dir, DICT_FILENAME)

    # 檢查輸入資料夾與字典
    if not os.path.exists(input_dir):
        print(f"❌ 找不到輸入資料夾: {input_dir}")
        return
    if not os.path.exists(dict_path):
        print(f"❌ 找不到字典檔: {dict_path}")
        return

    # 建立輸出資料夾
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 已建立輸出資料夾: {output_dir}")

    # 2. 預先載入字典 (只讀一次，提升效能)
    print(f"📖 正在載入字典 {DICT_FILENAME} ...")
    with open(dict_path, "r", encoding="utf-8") as f:
        dictionary = json.load(f)
    print("✅ 字典載入完成。")

    # 3. 遍歷資料夾內所有檔案
    files = [f for f in os.listdir(input_dir) if f.endswith(".json")]
    print(f"🔍 發現 {len(files)} 個 JSON 檔案，準備處理...")

    for filename in files:
        input_filepath = os.path.join(input_dir, filename)
        output_filepath = os.path.join(output_dir, f"aligned_{filename}")
        
        print(f"🚀 正在處理: {filename} ...")
        
        try:
            # Step A: 讀取原始檔案
            with open(input_filepath, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)

            # Step B: 執行 Syllable_decomposition01 (音節拆解)
            step1_data = Syllable_decomposition01.process_data_payload(raw_data)

            # Step C: 執行 Syllable_dictionary02 (結構分析)
            step2_data = Syllable_dictionary02.process_structure_payload(step1_data)

            # Step D: 執行 Align_syllables03 (拼音對齊)
            final_data = process_alignment_payload(step2_data, dictionary)

            # Step E: 寫入結果
            with open(output_filepath, "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)
            
            print(f"   💾 已儲存至: {output_filepath}")

        except Exception as e:
            print(f"   ⚠️ 處理 {filename} 時發生錯誤: {e}")

    print("\n🎉 所有檔案處理完成！")

if __name__ == "__main__":
    main()
