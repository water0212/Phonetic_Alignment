import numpy as np
import re
import json
import pandas as pd
import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
file_path = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE_PATH = os.path.join(file_path,'Ailgn_syllables', 'aligned_syllables.json')
OUTPUT_FILE_PATH =  os.path.join(file_path, 'output_alignment.xlsx')
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
        if not c_ch or not c_ts: return 0  # 一個有一空

        # 預設最低分 (不匹配)
        max_score = 0
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
        修復：現在會正確回傳 dir_matrix (方向矩陣) 供 Excel 顯示箭頭
        """
        n = len(ch_syllables)
        m = len(in_syllables)
        gap_penalty = 0 
        
        # 初始化 DP 表
        dp = np.zeros((n + 1, m + 1))
        
        # 初始化方向矩陣 (用來存箭頭符號的二維陣列)
        dir_matrix = [["" for _ in range(m + 1)] for _ in range(n + 1)]
        
        # 初始化邊界
        for i in range(1, n + 1):
            dp[i][0] = dp[i-1][0] + gap_penalty
            dir_matrix[i][0] = "↑" # 邊界只能往上
        for j in range(1, m + 1):
            dp[0][j] = dp[0][j-1] + gap_penalty
            dir_matrix[0][j] = "←" # 邊界只能往左
            
        # 填表
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                score = self.calculate_similarity(ch_syllables[i-1], in_syllables[j-1])
                
                match = dp[i-1][j-1] + score
                delete = dp[i-1][j] + gap_penalty
                insert = dp[i][j-1] + gap_penalty
                
                best_score = max(match, delete, insert)
                dp[i][j] = best_score
                
                # 記錄方向 (優先順序：Match > Delete > Insert)
                # 這些符號會顯示在 Excel 的格子裡
                if best_score == match:
                    dir_matrix[i][j] = "↖"
                elif best_score == delete:
                    dir_matrix[i][j] = "↑"
                else:
                    dir_matrix[i][j] = "←"
                
        # 回溯 (Backtracking) 找最佳路徑
        i, j = n, m
        alignment = []
        path_coords = [(i, j)] 
        
        while i > 0 or j > 0:
            current_score = dp[i][j]
            
            score_match = -9999
            if i > 0 and j > 0:
                sim = self.calculate_similarity(ch_syllables[i-1], in_syllables[j-1])
                score_match = dp[i-1][j-1] + sim
            
            score_del = dp[i-1][j] + gap_penalty if i > 0 else -9999
            
            # 回溯邏輯
            if i > 0 and j > 0 and abs(current_score - score_match) < 1e-5:
                alignment.append((ch_syllables[i-1], in_syllables[j-1], "已匹配"))
                i -= 1; j -= 1
            elif i > 0 and abs(current_score - score_del) < 1e-5:
                alignment.append((ch_syllables[i-1], None, "族語缺失"))
                i -= 1
            else:
                alignment.append((None, in_syllables[j-1], "中文缺失"))
                j -= 1
            
            path_coords.append((i, j))
        
        # 回傳這 4 個變數，Excel 生成函式就不會報錯了
        return alignment[::-1], dp, dir_matrix, path_coords
    def merge_syllables(self, syl_base, syl_append):

        new_rhyme = syl_base['rhyme'] + syl_append['onset'] + syl_append['rhyme']
        new_raw = syl_base.get('raw', '') + syl_append.get('raw', '')
        
        return {
            'onset': syl_base['onset'],
            'rhyme': new_rhyme,
            'raw': new_raw
        }

    def refine_alignment(self, original_alignment):
        """
        後處理：檢查「中文缺失」(即族語多出來的音節)，嘗試將其與前後音節合併，
        看分數是否變高，若變高則執行合併。
        """
        refined = []
        i = 0
        n = len(original_alignment)

        while i < n:
            ch_curr, ts_curr, status = original_alignment[i]

            # 我們只關心「中文缺失」的情況 (代表族語多了一個孤兒音節，如 wa)
            if status == "中文缺失" and ts_curr is not None:
                orphan = ts_curr
                
                # --- 1. 嘗試向左合併 (Merge Left) ---
                score_left = -999
                merged_left_ts = None
                
                # 確保左邊有東西，且左邊是「已匹配」的狀態
                if len(refined) > 0 and refined[-1][2] == "已匹配":
                    prev_ch = refined[-1][0]
                    prev_ts = refined[-1][1]
                    
                    # 模擬合併: se + wa
                    merged_left_ts = self.merge_syllables(prev_ts, orphan)
                    # 重新打分: shua vs sewa
                    score_left = self.calculate_similarity(prev_ch, merged_left_ts)

                # --- 2. 嘗試向右合併 (Merge Right) ---
                score_right = -999
                merged_right_ts = None
                
                # 確保右邊還有東西，且右邊是「已匹配」的狀態
                if i + 1 < n and original_alignment[i+1][2] == "已匹配":
                    next_ch = original_alignment[i+1][0]
                    next_ts = original_alignment[i+1][1]
                    
                    # 模擬合併: wa + ka (注意 orphan 在前)
                    merged_right_ts = self.merge_syllables(orphan, next_ts)
                    # 重新打分: ka vs waka
                    score_right = self.calculate_similarity(next_ch, merged_right_ts)

                # --- 3. 決策 PK ---
                # 設定一個門檻，例如合併後的分數至少要 > 0.5 (避免亂合併)
                threshold = 0.5 
                
                if score_left >= score_right and score_left > threshold:
                    # 向左合併勝出！
                    print(f"🔄 合併成功 (向左): {refined[-1][1]['raw']} + {orphan['raw']} -> {merged_left_ts['raw']}")
                    # 更新 refined 最後一筆資料
                    refined[-1] = (refined[-1][0], merged_left_ts, "已匹配(合併)")
                    i += 1 # 處理完孤兒，繼續
                    
                elif score_right > score_left and score_right > threshold:
                    # 向右合併勝出！
                    print(f"🔄 合併成功 (向右): {orphan['raw']} + {original_alignment[i+1][1]['raw']} -> {merged_right_ts['raw']}")
                    # 修改下一筆資料 (因為還沒進 refined，直接改 original_alignment 的下一筆)
                    original_alignment[i+1] = (original_alignment[i+1][0], merged_right_ts, "已匹配(合併)")
                    i += 1 # 跳過孤兒，因為它已經融入下一筆了
                    
                else:
                    # 兩邊都不討好，保持原樣
                    refined.append((ch_curr, ts_curr, status))
                    i += 1
            else:
                # 正常情況，直接加入
                refined.append((ch_curr, ts_curr, status))
                i += 1
                
        return refined


def parse_pinyin_string(pinyin_str):
    """
    將 "z,ong" 轉換為 {'onset': 'z', 'rhyme': 'ong', 'raw': 'zong'}
    """
    if not pinyin_str:
        return {'onset': '', 'rhyme': '', 'raw': ''}
    
    parts = pinyin_str.split(',')
    if len(parts) == 2:
        onset, rhyme = parts[0].strip(), parts[1].strip()
    else:
        # 處理沒有逗號的情況，假設全是韻母或根據需求調整
        onset, rhyme = "", pinyin_str.strip()
        
    return {
        'onset': onset,
        'rhyme': rhyme,
        'raw': onset + rhyme
    }

def process_json_to_excel(json_file_path, output_excel_path):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    aligner = PhoneticAligner()
    
    # 建立 Excel Workbook
    wb = Workbook()
    
    # --- Sheet 1: 對齊列表 (Summary) ---
    ws_summary = wb.active
    ws_summary.title = "對齊結果列表"
    headers = ["詞彙", "語意", "標準拼音", "實際拼音", "對齊視覺化", "狀態", "詳細分數"]
    ws_summary.append(headers)
    
    # --- Sheet 2: 矩陣視覺化 (Matrix Visualization) ---
    ws_matrix = wb.create_sheet("矩陣視覺化")
    
    # 定義樣式
    red_bold_font = Font(color="FF0000", bold=True)
    highlight_fill = PatternFill(start_color="FFFFCC", end_color="FFFFCC", fill_type="solid") # 淺黃色背景
    center_align = Alignment(horizontal='center', vertical='center')
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    current_matrix_row = 1 # 矩陣分頁的當前寫入行數

    print(f"正在處理 {len(data)} 筆資料...")

    for entry in data:
        raw_dict_pinyin = entry.get('dict_pinyin', [])
        raw_pinyin_info = entry.get('pinyin_info', [])
        
        ch_input = [parse_pinyin_string(s) for s in raw_dict_pinyin]
        ts_input = [parse_pinyin_string(s) for s in raw_pinyin_info]

        # 執行對齊，獲取矩陣資訊
        alignment_result, dp_matrix, dir_matrix, path_coords = aligner.align(ch_input, ts_input)
        final_alignment = aligner.refine_alignment(alignment_result)
        # --- 寫入 Sheet 1 (Summary) ---
        aligned_pairs = ["|"]
        status_list = []
        details_list = []
        for ch, ts, status in final_alignment:
            c_str = ch['raw'] if ch else "---"
            t_str = ts['raw'] if ts else "---"
            aligned_pairs.append(f"{c_str} ↔ {t_str} | ")
            status_list.append(status)
            if ch and ts:
                onset_score = aligner.calculate_consonant_score(ch['onset'], ts['onset'])
                dice_score = aligner.dice_coefficient(ch['rhyme'], ts['rhyme'])
                details_list.append(f"聲:{'Yes' if onset_score>0 else 'No'} | 韻:{dice_score:.2f}")
            else:
                details_list.append("---")

        ws_summary.append([
            entry.get('chinese', ''),
            entry.get('ch_semantic', ''),
            "-".join([str(s) if s else "" for s in raw_dict_pinyin]),
            "-".join([str(s) if s else "" for s in raw_pinyin_info]),
            "\n".join(aligned_pairs),
            ", ".join(status_list),
            "\n".join(details_list)
        ])

        # --- 寫入 Sheet 2 (Matrix) ---
        
        # 1. 寫入標題 (詞彙名稱)
        ws_matrix.cell(row=current_matrix_row, column=1, value=f"詞彙: {entry.get('chinese', '')}")
        ws_matrix.cell(row=current_matrix_row, column=1).font = Font(bold=True, size=12)
        current_matrix_row += 1

        # 2. 準備矩陣標頭
        # 縱軸 (Row Headers): 標準拼音 (Chinese) -> 對應 DP 的 i (0~n)
        row_headers = ["Start"] + [x['raw'] for x in ch_input]
        # 橫軸 (Col Headers): 實際拼音 (Tsou) -> 對應 DP 的 j (0~m)
        col_headers = ["Start"] + [x['raw'] for x in ts_input]

        # 3. 寫入橫軸標頭 (Column Headers)
        start_col_idx = 2 # 從 B 欄開始
        for idx, text in enumerate(col_headers):
            cell = ws_matrix.cell(row=current_matrix_row, column=start_col_idx + idx, value=text)
            cell.alignment = center_align
            cell.font = Font(bold=True)
            cell.border = thin_border

        current_matrix_row += 1

        # 4. 寫入矩陣內容
        n, m = dp_matrix.shape
        for i in range(n):
            # 寫入縱軸標頭 (Row Header)
            header_cell = ws_matrix.cell(row=current_matrix_row + i, column=1, value=row_headers[i])
            header_cell.alignment = center_align
            header_cell.font = Font(bold=True)
            header_cell.border = thin_border

            for j in range(m):
                val = dp_matrix[i][j]
                direction = dir_matrix[i][j]
                
                # 組合顯示文字: "↖ 2.5"
                display_text = f"{direction} {val:.2f}" if direction else f"{val:.2f}"
                
                cell = ws_matrix.cell(row=current_matrix_row + i, column=start_col_idx + j, value=display_text)
                cell.alignment = center_align
                cell.border = thin_border

                # 如果此格在最佳路徑上，進行高亮
                if (i, j) in path_coords:
                    cell.font = red_bold_font
                    cell.fill = highlight_fill

        current_matrix_row += n + 2 # 留白兩行準備下一個詞彙

    # 自動調整欄寬 (Sheet 1)
    for col in ws_summary.columns:
        length = max(len(str(cell.value)) for cell in col)
        ws_summary.column_dimensions[get_column_letter(col[0].column)].width = min(length + 2, 50)

    wb.save(output_excel_path)
    print(f"✅ 處理完成！結果已儲存至: {output_excel_path}")
    
dummy_json_content = [
    {
        "chinese": "總統府",
        "ch_semantic": "中譯",
        "pinyin_info": ["c,ong", "t,ong", "f,u"],
        "dict_pinyin": ["z,ong", "t,ong", "f,u"]
    },
    {
        "chinese": "光碟",
        "ch_semantic": "儲存媒體",
        "pinyin_info": ["k,uang", "t,i", "y,e"],
        "dict_pinyin": ["g,uang", "d,ie"]
    }
] 
# 實例化並執行
with open('input.json', 'w', encoding='utf-8') as f:
    json.dump(dummy_json_content, f, ensure_ascii=False, indent=2)

process_json_to_excel(INPUT_FILE_PATH, OUTPUT_FILE_PATH)

