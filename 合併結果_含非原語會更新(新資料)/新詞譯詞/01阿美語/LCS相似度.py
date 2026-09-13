import numpy as np
import re

class PhoneticAligner:
    def __init__(self):
        # 定義聲母群組 (根據你的需求)
        # 這裡將 Pinyin 和 族語拼音 混合在一起歸類
        self.consonant_chinese_groups = [
            {'b', 'p'},                     # 雙唇音
            {'m'},                          # 鼻音
            {'f'},                          # 唇齒音
            {'d', 't'},                     # 舌尖塞音
            {'n'},                          # 舌尖鼻音
            {'l', 'r'},                     # 液體音
            {'g', 'k'},
            {'d', 'j', 'z'},
            {'h'},
            {'j'},
            {'x'},
            {'t','q','c'},
            {'z', 'c', 's', 'zh', 'ch', 'sh'},
            {'d', 'j', 'z', 't', 'q', 'c'}
        ]
        self.consonant_tsou_groups = [
            {'b', 'p'},                     # 雙唇音
            {'m'},                          # 鼻音
            {'f'},                          # 唇齒音
            {'d', 't'},                     # 舌尖塞音
            {'n'},                          # 舌尖鼻音
            {'l', 'r'},                     # 液體音
            {'g', 'k', 'q'},
            {'d', 'j', 'z'},
            {'h'},
            {'j'},
            {'x'},
            {'t','c'},
            {'z', 'c', 's'},
            {'d', 'j', 'z', 't', 'c'}
        ]
        
        
        # 定義正規化映射 (用於 Dice 計算韻母相似度)
        # 讓 way 和 uai 能被視為相似
        self.vowel_map = {
            'w': 'u', 'y': 'i'
        }

    def calculate_consonant_score(self, c_ch, c_ts):
        """
        計算聲母相似度：遍歷所有群組，找出「含金量最高」的共同群組
        """
        # 0. 基本檢查
        if not c_ch and not c_ts: return 1  # 都是空聲母
        if not c_ch or not c_ts: return -1  # 一個有一空

        # 預設最低分 (不匹配)
        max_score = -1
        found_match = False

        # 1. 遍歷所有定義的群組
        # zip 讓我們同時拿到同一行的中文設定與族語設定
        for group_ch, group_ts in zip(self.consonant_chinese_groups, self.consonant_tsou_groups):
            
            # 2. 檢查是否「兩邊都符合」這一行的資格
            if c_ch in group_ch and c_ts in group_ts:
                found_match = True
                if(c_ch == c_ts):
                    current_score = 1
                
                # --- 分數公式設計 ---

                if group_ch == group_ts and group_ch == {'d', 'j', 'z', 't', 'q', 'c'}:
                    current_score = 0.7
                else:
                    current_score = 0.8
                # 確保分數不會扣到太低 (設個底限，例如 1 分，保證比不匹配好)
                current_score = max(current_score,0)

                # 4. 更新最高分
                if current_score > max_score:
                    max_score = current_score

        return max_score

    def dice_coefficient(self, s1, s2):
        """
        Dice 演算法：計算兩個字串的相似度
        Formula: 2 * |intersection| / (|s1| + |s2|)
        """
        if not s1 and not s2: return 1.0
        if not s1 or not s2: return 0.0
        
        # 1. 正規化 (把 w 變 u, y 變 i 以增加匹配率)
        def normalize(s):
            return "".join([self.vowel_map.get(char, char) for char in s.lower()])
        
        n1 = normalize(s1)
        n2 = normalize(s2)
        
        # 2. 轉成集合 (Set) 或 Bigram
        # 這裡用簡單的字元集合 (Character Set)，對於短音節效果不錯
        set1 = set(n1)
        set2 = set(n2)
        
        intersection = len(set1 & set2)
        total = len(set1) + len(set2)
        
        return (2.0 * intersection) / total if total > 0 else 0

    def calculate_similarity(self, syl_ch, syl_in):
        """
        計算兩個音節的相似分數
        輸入格式範例: {'onset': 'b', 'rhyme': 'u'}
        """
        # --- 1. 聲母分數 (類別比對) ---
        score_onset = self.calculate_consonant_score(syl_ch['onset'], syl_in['onset']) * 1
        
        

        # --- 2. 韻母分數 (Dice 係數) ---
        # 假設滿分是 6 分，用 Dice 係數 (0~1) 去乘
        dice = self.dice_coefficient(syl_ch['rhyme'], syl_in['rhyme'])
        score_rhyme = dice * 1
        
        return score_onset + score_rhyme

    def align(self, ch_syllables, in_syllables):
        """
        使用 Needleman-Wunsch 演算法進行對齊
        ch_syllables: 中文音節列表 [{'onset':'', 'rhyme':''}, ...]
        in_syllables: 族語音節列表
        """
        n = len(ch_syllables)
        m = len(in_syllables)
        gap_penalty = 0 # 空缺扣分
        
        # 初始化 DP 表
        dp = np.zeros((n + 1, m + 1))
        
        # 初始化邊界 (Gap 累積扣分)
        for i in range(1, n + 1):
            dp[i][0] = dp[i-1][0] + gap_penalty
        for j in range(1, m + 1):
            dp[0][j] = dp[0][j-1] + gap_penalty
            
        # 填表
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                # 計算相似度
                score = self.calculate_similarity(ch_syllables[i-1], in_syllables[j-1])
                
                match = dp[i-1][j-1] + score
                delete = dp[i-1][j] + gap_penalty
                insert = dp[i][j-1] + gap_penalty
                
                dp[i][j] = max(match, delete, insert)
                
        # 回溯 (Backtracking) 找最佳路徑
        i, j = n, m
        alignment = []
        
        while i > 0 or j > 0:
            current_score = dp[i][j]
            
            # 重新計算分數以判斷來源
            score_match = -9999
            if i > 0 and j > 0:
                sim = self.calculate_similarity(ch_syllables[i-1], in_syllables[j-1])
                score_match = dp[i-1][j-1] + sim
            
            score_del = dp[i-1][j] + gap_penalty if i > 0 else -9999
            score_ins = dp[i][j-1] + gap_penalty if j > 0 else -9999
            
            # 優先順序：對角線(Match) > 上(Skip CH) > 左(Skip IN)
            # 使用浮點數比較時要小心誤差，這裡用簡單比較
            if i > 0 and j > 0 and abs(current_score - score_match) < 1e-5:
                # 對齊成功
                alignment.append((ch_syllables[i-1], in_syllables[j-1], "MATCH"))
                i -= 1
                j -= 1
            elif i > 0 and abs(current_score - score_del) < 1e-5:
                # 中文多出來 (族語缺)
                alignment.append((ch_syllables[i-1], None, "DEL_IN"))
                i -= 1
            else:
                # 族語多出來 (中文缺)
                alignment.append((None, in_syllables[j-1], "INS_IN"))
                j -= 1
                
        return alignment[::-1] # 反轉回來

# --- 測試資料與執行 ---

# 模擬輸入資料 (已經拆好聲韻母)
# 範例：光碟 (Guang-Die) vs Kuang-ti-ye
chinese_data = [
    {'onset': 'h', 'rhyme': 'uan', 'raw': 'huan'},
    {'onset': 'b', 'rhyme': 'ao',   'raw': 'bao'},
    {'onset': 'sh', 'rhyme': 'u',   'raw': 'shu'}
]

tsou_data = [
    {'onset': 'h', 'rhyme': 'u', 'raw': 'hu'},
    {'onset': 'w', 'rhyme': 'an','raw': 'wan'},
    {'onset': 'p', 'rhyme': 'aw','raw': 'paw'},
    {'onset': 's','rhyme': 'u','raw': 'su'}
    
]

# 實例化並執行
aligner = PhoneticAligner()
result = aligner.align(chinese_data, tsou_data)

# --- 輸出結果 ---
print(f"{'中文音節':<15} {'族語音節':<15} {'關係':<10} {'詳細分數'}")
print("-" * 50)

for ch, ts, status in result:
    ch_str = ch['raw'] if ch else "---"
    ts_str = ts['raw'] if ts else "---"
    
    detail = ""
    if ch and ts:
        onset_score = aligner.calculate_consonant_score(ch['onset'], ts['onset'])
        dice = aligner.dice_coefficient(ch['rhyme'], ts['rhyme'])
        detail = f"聲母同組:{'Yes' if onset_score>0 else 'No'}, 韻母Dice:{dice:.2f}"
        
    print(f"{ch_str:<15} {ts_str:<15} {status:<10} {detail}")