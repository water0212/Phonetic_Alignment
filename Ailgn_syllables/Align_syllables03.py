import os
import json
from Syllable_dictionary02 import model_main

file_path = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE_PATH = os.path.join(file_path,'Ailgn_syllables', 'aligned_syllables.json')
OUTPUT_FILE_PATH =  os.path.join(file_path, 'output_alignment.xlsx')

class PhoneticAligner:
    def __init__(self):
        # 定義聲母群組 (根據你的需求)
        # 這裡將 Pinyin 和 族語拼音 混合在一起歸類
        self.consonant_chinese_groups = [
            {'b', 'p'}, 
            {'m'}, 
            {'f'}, 
            {'d', 't'}, 
            {'n'}, 
            {'l', 'r'},
            {'g', 'k'}, 
            {'d', 'j', 'z'}, 
            {'h'}, 
            {'j'}, 
            {'x'},
            {'t','q','c'}, 
            {'z', 'c', 's', 'zh', 'ch', 'sh'},
            {'d', 'j', 'z', 't', 'q', 'c'},
            {'f'}
        ]
        self.consonant_tsou_groups = [
            {'b', 'p'}, 
            {'m'}, 
            {'f'}, 
            {'d', 't'}, 
            {'n'}, 
            {'l', 'r'},
            {'g', 'k', 'q', '’', '^'}, 
            {'d', 'j', 'z'}, 
            {'h'}, 
            {'j'}, 
            {'x'},
            {'t','c'}, 
            {'z', 'c', 's'}, 
            {'d', 'j', 'z', 't', 'c'},
            {'f','v', 'b'}
        ]
        
        
        # 定義正規化映射 (用於 Dice 計算韻母相似度)
        # 讓 way 和 uai 能被視為相似
        self.vowel_map = {
            'w': 'u', 'y': 'i'
        }
    def calculate_consonant_score(self, c_ch, c_ts):
        """
        聲母比對：同一群組 0.8分，完全相同 1分
        群組：雙唇{b,p}、舌尖{d,t}、舌根{g,k,q} 等 14組
        """
        if not c_ch and not c_ts: return 1
        if not c_ch or not c_ts: return 0
        
        max_score = 0
        for group_ch, group_ts in zip(self.consonant_chinese_groups, self.consonant_tsou_groups):
            if c_ch in group_ch and c_ts in group_ts:
                current_score = 1 if c_ch == c_ts else 0.8  # 相同1分，類別0.8
                max_score = max(max_score, current_score)
        return max_score

    def dice_coefficient(self, s1, s2):
        
        # Dice: 2 * LCS(s1, s2) / (|s1| + |s2|)
        # 使用 LCS (最長公共子序列) 演算法計算 intersection，
        # 這樣可以考慮字母順序 (例如 'an' 和 'na' 不會被視為一樣)。
        # 正規化：w→u, y→i 增加匹配率
        
        # 1. 正規化字串 (處理 w, y)
        def normalize(s): return "".join(self.vowel_map.get(c, c) for c in s.lower())
        
        n1, n2 = normalize(s1), normalize(s2)
        len1, len2 = len(n1), len(n2)
        
        # 若有空字串，相似度為 0
        if len1 == 0 or len2 == 0:
            return 0.0

        # 2. 使用動態規劃 (DP) 計算 LCS 長度
        # 建立一個 (len1+1) x (len2+1) 的二維陣列，初始值為 0
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if n1[i - 1] == n2[j - 1]:
                    # 如果字元相同，則長度 + 1
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    # 如果不同，取左邊或上面的最大值 (繼承之前的最長長度)
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        # dp矩陣右下角即為最長公共子序列的長度
        intersection = dp[len1][len2]

        # 3. 計算 Dice Coefficient
        return 2.0 * intersection / (len1 + len2)


    def calculate_similarity(self, syl_ch, syl_in):
        """
        總分 = 聲母(1分) + 韻母(1分)
        syl_ch/syl_in: {'onset': 'b', 'rhyme': 'u'}
        """
        score_onset = self.calculate_consonant_score(syl_ch['onset'], syl_in['onset'])
        dice = self.dice_coefficient(syl_ch['rhyme'], syl_in['rhyme'])
        score_rhyme = dice
        return score_onset + score_rhyme


def find_word_in_dict(word, dictionary, pinyin_info):
    """在字典中尋找單詞，返回其拼音列表"""
    Ph = PhoneticAligner()
    pinyin = [None] * len(word)
    cnt = 0
    for entry in dictionary:
        key = entry.get("traditional", "")
        if key in word:
            cnt += 1
            entry_pinyin = entry.get('pronunciations', [])
            sum = -100
            for p in entry_pinyin:
                initial = p.get('initial', '') if entry_pinyin else ''
                final = p.get('final', '') if entry_pinyin else ''
                for info in pinyin_info:
                    ini, fin = info.split(",") if "," in info else ("", "")
                    tmp = max(sum, Ph.calculate_similarity({'onset': initial, 'rhyme': final}, {'onset': ini, 'rhyme': fin}))
                if tmp > sum:
                    sum = tmp
                    pinyin[word.index(key)] = initial + "," + final
        if cnt >= len(word) + 1:  # 已找到足夠的拼音
            break
    
    return pinyin

def process_file(input_data: str, dict_path: str, output_path: str):
    # if not os.path.exists(input_path):
    #     print(f"❌ {input_path}")
    #     return
    if not os.path.exists(dict_path):
        print(f"❌ {dict_path}")
        return
    
    data = json.loads(input_data)
    
    with open(dict_path, "r", encoding="utf-8") as f:
        dictionary = json.load(f)
    
    result = []
    for item in data:
        word = item.get("chinese_word", "")
        # print(f"處理: {word}")
        ch_semantic = item.get("ch_semantic", "")
        syllable_structure = item.get("syllable_structure", [])
        pinyin_info = []
        for syl in syllable_structure:
            pinyin_info.append(syl.get("split_display", ""))
        pinyin_ch = find_word_in_dict(word, dictionary,pinyin_info)
        result.append({
            "chinese": word,
            "ch_semantic": ch_semantic,
            "pinyin_info": pinyin_info,
            "dict_pinyin": pinyin_ch
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # input_data 可以允許放入還未處理過的merged_output.json，或是已經處理過的音節轉字典.json，根據你的需求選擇
    input_data = model_main(os.path.join(file_path, "merged_output.json"))
    dict_file = os.path.join(file_path, "cedict_normalized.json")
    output_file = os.path.join(file_path, "aligned_syllables.json")
    process_file(input_data, dict_file, output_file)