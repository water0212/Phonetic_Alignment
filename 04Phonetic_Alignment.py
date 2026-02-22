import numpy as np
import re
import json
import pandas as pd
import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

file_path = os.path.dirname(os.path.abspath(__file__))
# 請根據需求調整輸入輸出路徑
INPUT_FILE_PATH = os.path.join(file_path, 'Ailgn_syllables', 'aligned_syllables.json')
OUTPUT_FILE_PATH =  os.path.join(file_path, 'output_alignment_refined.xlsx')

class PhoneticAligner:
    def __init__(self):
        # 定義聲母群組
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
            {'f'},
            {'ㄜ'},
            {'i'}
            
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
            {'f','v', 'b'},
            {'o', 'e','u','é'},
            {'ɨ','ʉ', 'y'}
        ]
        
        # 定義正規化映射
        self.vowel_map = {'w': 'u', 'y': 'i'}

    def calculate_consonant_score(self, c_ch, c_ts):
        if c_ch == "0c" and c_ts == "0c": return 1
        if c_ch == "0c" or  c_ts == "0c": return 0

        max_score = 0
        
        for group_ch, group_ts in zip(self.consonant_chinese_groups, self.consonant_tsou_groups):
            if c_ch in group_ch and c_ts in group_ts:
                if c_ch == c_ts:
                    current_score = 1
                elif group_ch == group_ts and group_ch == {'d', 'j', 'z', 't', 'q', 'c'}:
                    current_score = 0.7
                else:
                    current_score = 0.8
                
                current_score = max(current_score, 0)
                if current_score > max_score:
                    max_score = current_score

        return max_score

    def dice_coefficient(self, s1, s2):
        if s1 == "0v" and s2 == "0v": return 1.0
        if s1 == "0v" or s2 == "0v": return 0.0
        
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
        # 聲母分數
        score_onset = self.calculate_consonant_score(syl_ch['onset'], syl_in['onset']) * 1
        # 韻母分數
        score_rhyme = self.dice_coefficient(syl_ch['rhyme'], syl_in['rhyme']) * 1
        
        return score_onset + score_rhyme

    def align(self, ch_syllables, in_syllables):
        """
        Needleman-Wunsch 對齊演算法
        """
        n = len(ch_syllables)
        m = len(in_syllables)
        gap_penalty = 0 
        
        dp = np.zeros((n + 1, m + 1))
        # 修正處：初始化為空字串
        dir_matrix = [["" for _ in range(m + 1)] for _ in range(n + 1)]
        
        for i in range(1, n + 1):
            dp[i][0] = dp[i-1][0] + gap_penalty
            dir_matrix[i][0] = "↑"
        for j in range(1, m + 1):
            dp[0][j] = dp[0][j-1] + gap_penalty
            dir_matrix[0][j] = "←"
            
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                score = self.calculate_similarity(ch_syllables[i-1], in_syllables[j-1])
                
                match = dp[i-1][j-1] + score
                delete = dp[i-1][j] + gap_penalty
                insert = dp[i][j-1] + gap_penalty
                
                best_score = max(match, delete, insert)
                dp[i][j] = best_score
                
                if best_score == match:
                    dir_matrix[i][j] = "↖"
                elif best_score == delete:
                    dir_matrix[i][j] = "↑"
                else:
                    dir_matrix[i][j] = "←"
                
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
        
        return alignment[::-1], dp, dir_matrix, path_coords

    def merge_syllables(self, syl_base, syl_append):
        append_onset = syl_append['onset']    
        # if append_onset == '0c':
        #     append_onset = ''
        
        new_rhyme = syl_base['rhyme'] + append_onset + syl_append['rhyme']
        new_raw = syl_base.get('raw', '') + syl_append.get('raw', '')
        
        return {
            'onset': syl_base['onset'],
            'rhyme': new_rhyme,
            'raw': new_raw
        }

    def refine_alignment(self, original_alignment):
        """
        多次迴圈合併版 (Iterative Merge)
        邏輯：
        1. 使用 while True 迴圈，不斷掃描列表。
        2. 針對每一個「中文缺失」(多餘族語)，計算「併入左邊」vs「併入右邊」的分數差 (Delta)。
        3. 選擇分數提升最多的一邊進行合併。
        4. 如果發生了向右合併，我們將當前音節併入「下一個」音節，這樣下一輪掃描時，它就能繼續帶著走 (解決 u -> a -> i 連鎖問題)。
        5. 當某一輪完全沒有發生任何合併時，結束迴圈。
        """
        current_alignment = original_alignment
        
        while True:
            has_changed = False
            new_alignment = []
            n = len(current_alignment)
            i = 0
            
            while i < n:
                ch_curr, ts_curr, status = current_alignment[i]
                
                # 只有「中文缺失」(多餘的族語音節) 需要被處理
                if status == "中文缺失" and ts_curr is not None:
                    orphan = ts_curr
                    
                    # 初始化 Delta (分數變化量)
                    delta_left = -float('inf')
                    merged_left_ts = None
                    
                    delta_right = -float('inf')
                    merged_right_ts = None
                    
                    # --- 1. 評估向左合併 (Merge Left) ---
                    # 左邊的對象是 new_alignment 的最後一個元素
                    if len(new_alignment) > 0 and new_alignment[-1][2] in ["已匹配", "已匹配(合併)"]:
                        prev_ch = new_alignment[-1][0]
                        prev_ts = new_alignment[-1][1]
                        
                        score_orig = self.calculate_similarity(prev_ch, prev_ts)
                        temp_merged = self.merge_syllables(prev_ts, orphan) # Left + Orphan
                        score_new = self.calculate_similarity(prev_ch, temp_merged)
                        
                        delta_left = score_new - score_orig
                        merged_left_ts = temp_merged
                        
                    # --- 2. 評估向右合併 (Merge Right) ---
                    # 右邊的對象是 current_alignment 的下一個元素 (i+1)
                    if i + 1 < n and current_alignment[i+1][2] in ["已匹配", "已匹配(合併)"]:
                        next_ch = current_alignment[i+1][0]
                        next_ts = current_alignment[i+1][1]
                        
                        score_orig = self.calculate_similarity(next_ch, next_ts)
                        temp_merged = self.merge_syllables(orphan, next_ts) # Orphan + Right
                        score_new = self.calculate_similarity(next_ch, temp_merged)
                        
                        delta_right = score_new - score_orig
                        merged_right_ts = temp_merged
                    
                    # --- 3. 決策與執行 ---
                    
                    # 如果兩邊都不能合，直接保留原樣
                    if delta_left == -float('inf') and delta_right == -float('inf'):
                        new_alignment.append((ch_curr, ts_curr, status))
                        i += 1
                        continue
                        
                    # 比較哪邊分數提升更多
                    if delta_left >= delta_right:
                        # ✅ 向左合併勝出
                        # 更新 new_alignment 的最後一個元素
                        # print(f"🔄 合併 (向左): {new_alignment[-1][1]['raw']} + {orphan['raw']} (Δ: {delta_left:.2f})")
                        new_alignment[-1] = (new_alignment[-1][0], merged_left_ts, "已匹配(合併)")
                        has_changed = True
                        i += 1 # 當前 orphan 已經被吸收到左邊了，跳過
                    else:
                        # ✅ 向右合併勝出
                        # 這是解決連鎖問題的關鍵：我們修改 current_alignment[i+1]
                        # 這樣當前 orphan 就被「推」到下一個格子裡了
                        # print(f"🔄 合併 (向右): {orphan['raw']} + {current_alignment[i+1][1]['raw']} (Δ: {delta_right:.2f})")
                        
                        target_next = current_alignment[i+1]
                        current_alignment[i+1] = (target_next[0], merged_right_ts, "已匹配(合併)")
                        
                        has_changed = True
                        i += 1 # 當前 orphan 已經被吸收到右邊了(也就是 i+1)，跳過
                else:
                    # 正常節點，直接加入
                    new_alignment.append((ch_curr, ts_curr, status))
                    i += 1
            
            # 更新列表
            current_alignment = new_alignment
            
            # 如果這一輪完全沒有任何變動，代表已經最佳化完成，跳出迴圈
            if not has_changed:
                break
                
        return current_alignment


def parse_pinyin_string(pinyin_str):
    if not pinyin_str:
        return {'onset': '', 'rhyme': '', 'raw': ''}
    
    parts = pinyin_str.split(',')
    if len(parts) == 2:
        onset, rhyme = parts[0].strip(), parts[1].strip()
    else:
        onset, rhyme = "", pinyin_str.strip()
        
    return {
        'onset': onset,
        'rhyme': rhyme,
        'raw': onset + rhyme
    }

def process_json_to_excel(json_file_path, output_excel_path):
    # 讀取 JSON (如果檔案不存在，使用範例資料)
    if not os.path.exists(json_file_path):
        print(f"找不到檔案 {json_file_path}，將使用範例資料生成...")
        data = [
            {
                "chinese": "範例詞",
                "ch_semantic": "測試",
                "pinyin_info": ["s,e", "w,a", "k,a"], # 故意多一個 wa
                "dict_pinyin": ["sh,ua", "k,a"]
            }
        ]
    else:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

    aligner = PhoneticAligner()
    wb = Workbook()
    
    # --- Sheet 1: 對齊列表 ---
    ws_summary = wb.active
    ws_summary.title = "對齊結果列表"
    headers = ["詞彙", "語意", "標準拼音", "實際拼音", "對齊視覺化", "狀態", "詳細分數"]
    ws_summary.append(headers)
    
    # --- Sheet 2: 矩陣視覺化 ---
    ws_matrix = wb.create_sheet("矩陣視覺化")
    
    # 樣式設定
    red_bold_font = Font(color="FF0000", bold=True)
    highlight_fill = PatternFill(start_color="FFFFCC", end_color="FFFFCC", fill_type="solid")
    center_align = Alignment(horizontal='center', vertical='center')
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    current_matrix_row = 1

    print(f"正在處理 {len(data)} 筆資料...")

    for entry in data:
        raw_dict_pinyin = entry.get('dict_pinyin', [])
        raw_pinyin_info = entry.get('pinyin_info', [])
        
        ch_input = [parse_pinyin_string(s) for s in raw_dict_pinyin]
        ts_input = [parse_pinyin_string(s) for s in raw_pinyin_info]

        # 1. 執行 Needleman-Wunsch 對齊 (產生矩陣)
        alignment_result, dp_matrix, dir_matrix, path_coords = aligner.align(ch_input, ts_input)
        
        # 2. 執行 Refine (合併孤兒音節)
        final_alignment = aligner.refine_alignment(alignment_result)
        
        # --- 寫入 Sheet 1 ---
        aligned_pairs = ["|"]
        status_list = []
        details_list = []
        for ch, ts, status in final_alignment:
            c_str = ch['raw'] if ch else "---"
            t_str = ts['raw'] if ts else "---"
            c_str = c_str.replace("0c", "")  # 移除 '0c' 表示的無聲母
            t_str = t_str.replace("0c", "")
            c_str = c_str.replace("0v", "")  # 移除 '0v' 表示的無韻母
            t_str = t_str.replace("0v", "")
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

        # --- 寫入 Sheet 2 (矩陣視覺化) ---
        ws_matrix.cell(row=current_matrix_row, column=1, value=f"詞彙: {entry.get('chinese', '')}")
        ws_matrix.cell(row=current_matrix_row, column=1).font = Font(bold=True, size=12)
        current_matrix_row += 1

        row_headers = ["Start"] + [x['raw'] for x in ch_input]
        col_headers = ["Start"] + [x['raw'] for x in ts_input]

        start_col_idx = 2
        for idx, text in enumerate(col_headers):
            cell = ws_matrix.cell(row=current_matrix_row, column=start_col_idx + idx, value=text)
            cell.alignment = center_align
            cell.font = Font(bold=True)
            cell.border = thin_border

        current_matrix_row += 1

        n_rows, m_cols = dp_matrix.shape
        for i in range(n_rows):
            header_cell = ws_matrix.cell(row=current_matrix_row + i, column=1, value=row_headers[i])
            header_cell.alignment = center_align
            header_cell.font = Font(bold=True)
            header_cell.border = thin_border

            for j in range(m_cols):
                val = dp_matrix[i][j]
                direction = dir_matrix[i][j]
                display_text = f"{direction} {val:.2f}" if direction else f"{val:.2f}"
                
                cell = ws_matrix.cell(row=current_matrix_row + i, column=start_col_idx + j, value=display_text)
                cell.alignment = center_align
                cell.border = thin_border

                if (i, j) in path_coords:
                    cell.font = red_bold_font
                    cell.fill = highlight_fill

        current_matrix_row += n_rows + 2

    # 自動調整欄寬
    for col in ws_summary.columns:
        length = max(len(str(cell.value)) for cell in col)
        ws_summary.column_dimensions[get_column_letter(col[0].column)].width = min(length + 2, 50)

    try:
        wb.save(output_excel_path)
        print(f"✅ 處理完成！結果已儲存至: {output_excel_path}")
    except Exception as e:
        print(f"❌ 儲存檔案失敗 (請檢查檔案是否被開啟): {e}")

if __name__ == "__main__":
    process_json_to_excel(INPUT_FILE_PATH, OUTPUT_FILE_PATH)
