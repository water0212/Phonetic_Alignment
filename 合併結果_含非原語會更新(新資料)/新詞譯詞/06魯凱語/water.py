import json
import re
import os
import pandas as pd

# --- 路徑設定 ---
file_path = os.path.dirname(os.path.abspath(__file__))
folder_name = os.path.basename(file_path)
input_file_name = f"merged_output.json" 
input_full_path = os.path.join(file_path, input_file_name)
output_file_name = f"{folder_name}_拆解結果.xlsx"
output_full_path = os.path.join(file_path, output_file_name)

class Syllabifier:
    def __init__(self):
        # 定義二合字母 (Digraphs) 與對應的暫時替身符號
        # 這裡選用一些不會出現在拼音裡的特殊符號
        self.digraph_map = {
            "ts": "§",
            "ng": "Ω",
            "ny": "¥",
            "sy": "µ",
            "dr": "¶",
            "tj": "·",
            "dj": "¸",
            "lj": "¹",
            "tr": "º",
            "ll": "»",
            "lr": "¼",
            "dh": "½",
            "th": "¾",  
            "sh": "¿",
            "hl": "À",
            
        }
        # 為了正確替換，必須先換長的 (如果有三合字母要放前面)
        self.sorted_digraphs = sorted(self.digraph_map.keys(), key=len, reverse=True)
        
        # 反向對照表 (還原用)
        self.reverse_map = {v: k for k, v in self.digraph_map.items()}
        
        self.vowels = "aeiou"

    def mask_word(self, word):
        """將二合字母替換成單一特殊字元"""
        masked = word
        for dg in self.sorted_digraphs:
            # 使用 re.IGNORECASE 確保大小寫都能抓到 (如 Ts, TS)
            # 但替換時我們先統一換成特殊符號，還原時再決定大小寫(這裡簡化為小寫還原，或保留原樣邏輯需更複雜)
            # 這裡為了簡單，我們假設輸入都是小寫，或者我們只處理小寫
            pattern = re.compile(re.escape(dg), re.IGNORECASE)
            masked = pattern.sub(self.digraph_map[dg], masked)
        return masked

    def restore_word(self, syllables_str):
        """將特殊字元還原回二合字母"""
        restored = syllables_str
        for char, original in self.reverse_map.items():
            restored = restored.replace(char, original)
        return restored

    def split_syllables(self, word):
        # 1. 變身：處理二合字母
        masked_word = self.mask_word(word)
        
        # 2. 切割邏輯：使用「母音」作為錨點來切分
        # re.split 會保留括號內的 separator (母音)，所以會變成 ['S', 'i', 'n§', 'u', 'Ωy', 'a', 'n']
        parts = re.split(f"([{self.vowels}]+)", masked_word, flags=re.IGNORECASE)
        
        # 過濾空字串
        parts = [p for p in parts if p]
        
        if not parts:
            return word

        syllables = []
        
        # 邏輯：重組 [子音群1, 母音1, 子音群2, 母音2, 子音群3...]
        # 我們採用「最大聲母原則 (Maximal Onset)」的簡化版：
        # 兩個母音中間的子音群，最後一個子音歸給下一個音節當聲母，剩下的歸給上一個音節當韻尾。
        
        # 初始化：先抓第一組 (聲母+母音)
        current_syllable = ""
        
        # 遍歷 parts，通常結構是 C-V-C-V...
        # 但 re.split 出來可能是 [C, V, C, V, C]
        
        idx = 0
        while idx < len(parts):
            part = parts[idx]
            
            # 檢查這部分是不是母音
            if re.match(f"^[{self.vowels}]+$", part, re.IGNORECASE):
                # 如果是母音，加到當前音節
                current_syllable += part
                
                # 檢查下一個部分 (Intervocalic Consonants - 母音間的子音)
                if idx + 1 < len(parts):
                    next_part = parts[idx+1]
                    
                    # 如果下一個部分是最後結尾 (後面沒母音了)，全部收進來當韻尾
                    if idx + 2 >= len(parts):
                        current_syllable += next_part
                        syllables.append(current_syllable)
                        idx += 2 # 跳過 next_part
                    else:
                        # 如果後面還有母音，表示 next_part 是夾在兩個母音中間的子音群
                        # 例如 'n§' (n + ts)
                        consonant_cluster = next_part
                        
                        if len(consonant_cluster) == 0:
                            # 沒子音，直接切
                            syllables.append(current_syllable)
                            current_syllable = ""
                        elif len(consonant_cluster) == 1:
                            # 只有一個子音 (例如 't')，通常歸給下一個音節當聲母
                            syllables.append(current_syllable)
                            current_syllable = consonant_cluster
                        else:
                            # 有多個子音 (例如 'n§')
                            # 切割規則：最後一個字元給下一個音節，前面全部留給當前音節
                            # n§ -> n 留著, § 給下一個
                            coda = consonant_cluster[:-1]
                            onset = consonant_cluster[-1]
                            
                            current_syllable += coda
                            syllables.append(current_syllable)
                            current_syllable = onset
                        
                        idx += 2 # 跳過 next_part (因為已經處理了)
                else:
                    # 已經是最後了
                    syllables.append(current_syllable)
                    idx += 1
            else:
                # 如果是子音開頭 (例如單字的起頭)
                current_syllable += part
                idx += 1
        
        # 3. 還原並組合
        result_str = "-".join(syllables)
        return self.restore_word(result_str)

# 實例化工具
syllabifier = Syllabifier()

def analyze_tsou_word(chinese_key, word_data):
    try:
        fm_word = word_data['new_word'][0]['fm_word']
        semantic = word_data['new_word'][0]['ch_semantic']
    except (KeyError, IndexError):
        return {"中文詞彙": chinese_key, "原詞": "資料錯誤", "結構類型": "", "音節拆解": "", "原始備註": ""}
    
    # 1. 物理分割 (處理空格)
    tokens = re.split(r'[ -]', fm_word)
    tokens = [t for t in tokens if t]
    
    structure_type = "單詞"
    if len(tokens) > 1:
        structure_type = "片語"

    # 2. 音節拆解 (使用新的類別方法)
    decomposed_tokens = []
    for token in tokens:
        # 呼叫拆解函式
        decomposed = syllabifier.split_syllables(token)
        decomposed_tokens.append(decomposed)
    
    return {
        "中文詞彙": chinese_key,
        f"{folder_name}原詞": fm_word,
        "結構類型": structure_type,
        "音節拆解": " | ".join(decomposed_tokens),
        "原始備註": semantic
    }

# --- 主程式 ---
data = {}
if os.path.exists(input_full_path):
    print(f"正在讀取檔案: {input_full_path}")
    with open(input_full_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
else:
    print(f"⚠️ 找不到檔案: {input_full_path}")

all_results = []
for key, value in data.items():
    result = analyze_tsou_word(key, value)
    all_results.append(result)

if all_results:
    df = pd.DataFrame(all_results)
    cols = ["中文詞彙", f"{folder_name}原詞", "音節拆解", "結構類型", "原始備註"]
    df = df[cols]
    try:
        df.to_excel(output_full_path, index=False, engine='openpyxl')
        print(f"✅ 成功！結果已儲存至: {output_full_path}")
    except Exception as e:
        print(f"❌ 儲存失敗: {e}")