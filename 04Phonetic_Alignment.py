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
            {'b', 'p'}, {'m'}, {'f'}, {'d', 't'}, {'n'}, {'l', 'r'},
            {'g', 'k'}, {'d', 'j', 'z'}, {'h'}, {'j'}, {'x'},
            {'t','q','c'}, {'z', 'c', 's', 'zh', 'ch', 'sh'},
            {'d', 'j', 'z', 't', 'q', 'c'}
        ]
        self.consonant_tsou_groups = [
            {'b', 'p'}, {'m'}, {'f'}, {'d', 't'}, {'n'}, {'l', 'r'},
            {'g', 'k', 'q'}, {'d', 'j', 'z'}, {'h'}, {'j'}, {'x'},
            {'t','c'}, {'z', 'c', 's'}, {'d', 'j', 'z', 't', 'c'}
        ]
        
        # 定義正規化映射
        self.vowel_map = {'w': 'u', 'y': 'i'}

    def calculate_consonant_score(self, c_ch, c_ts):
        if not c_ch and not c_ts: return 1
        if not c_ch or not c_ts: return 0

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
        if not s1 and not s2: return 1.0
        if not s1 or not s2: return 0.0
        
        def normalize(s):
            return "".join([self.vowel_map.get(char, char) for char in s.lower()])
        
        n1 = normalize(s1)
        n2 = normalize(s2)
        
        set1 = set(n1)
        set2 = set(n2)
        
        intersection = len(set1 & set2)
        total = len(set1) + len(set2)
        
        return (2.0 * intersection) / total if total > 0 else 0

    def calculate_similarity(self, syl_ch, syl_in):
        # 聲母分數
        score_onset = self.calculate_consonant_score(syl_ch['onset'], syl_in['onset']) * 1
        # 韻母分數
        dice = self.dice_coefficient(syl_ch['rhyme'], syl_in['rhyme'])
        score_rhyme = dice * 1
        
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
        new_rhyme = syl_base['rhyme'] + syl_append['onset'] + syl_append['rhyme']
        new_raw = syl_base.get('raw', '') + syl_append.get('raw', '')
        
        return {
            'onset': syl_base['onset'],
            'rhyme': new_rhyme,
            'raw': new_raw
        }

    def refine_alignment(self, original_alignment):
        """
        修正後的合併邏輯：
        1. 計算合併前後的分數差異 (Delta)。
        2. 比較向左合併 (Delta_Left) 與 向右合併 (Delta_Right)。
        3. 選擇 Delta 較大者 (即使兩者都為負，選相對高的)。
        """
        refined = []
        i = 0
        n = len(original_alignment)

        while i < n:
            ch_curr, ts_curr, status = original_alignment[i]

            # 針對「中文缺失」(即多餘的族語音節)
            if status == "中文缺失" and ts_curr is not None:
                orphan = ts_curr
                
                # 初始化差異分數 (設為極小值代表不可行)
                delta_left = -float('inf')
                merged_left_ts = None
                
                delta_right = -float('inf')
                merged_right_ts = None
                
                # --- 1. 評估向左合併 ---
                # 確保左邊有已匹配的項目
                if len(refined) > 0 and refined[-1][2] in ["已匹配", "已匹配(合併)"]:
                    prev_ch = refined[-1][0]
                    prev_ts = refined[-1][1]
                    
                    # 原始分數
                    score_orig = self.calculate_similarity(prev_ch, prev_ts)
                    # 合併後分數
                    temp_merged = self.merge_syllables(prev_ts, orphan)
                    score_new = self.calculate_similarity(prev_ch, temp_merged)
                    
                    delta_left = score_new - score_orig
                    merged_left_ts = temp_merged

                # --- 2. 評估向右合併 ---
                # 確保右邊有已匹配的項目
                if i + 1 < n and original_alignment[i+1][2] in ["已匹配", "已匹配(合併)"]:
                    next_ch = original_alignment[i+1][0]
                    next_ts = original_alignment[i+1][1]
                    
                    # 原始分數
                    score_orig = self.calculate_similarity(next_ch, next_ts)
                    # 合併後分數 (Orphan 在前)
                    temp_merged = self.merge_syllables(orphan, next_ts)
                    score_new = self.calculate_similarity(next_ch, temp_merged)
                    
                    delta_right = score_new - score_orig
                    merged_right_ts = temp_merged

                # --- 3. 決策 PK ---
                # 如果兩邊都無法合併 (例如孤兒卡在邊界且無鄰居)，只能保留
                if delta_left == -float('inf') and delta_right == -float('inf'):
                    refined.append((ch_curr, ts_curr, status))
                    i += 1
                    continue

                # 比較 Delta (選大的)
                # 邏輯：
                # - 若兩邊 Delta > 0 -> 選大的 (兩邊都變高選比較高的)
                # - 若兩邊 Delta < 0 -> 選大的 (都沒有變高選相對高的/扣分少的)
                if delta_left >= delta_right:
                    # 向左合併勝出
                    print(f"🔄 合併 (向左): {refined[-1][1]['raw']} + {orphan['raw']} (Δ: {delta_left:.2f})")
                    refined[-1] = (refined[-1][0], merged_left_ts, "已匹配(合併)")
                    i += 1
                else:
                    # 向右合併勝出
                    print(f"🔄 合併 (向右): {orphan['raw']} + {original_alignment[i+1][1]['raw']} (Δ: {delta_right:.2f})")
                    original_alignment[i+1] = (original_alignment[i+1][0], merged_right_ts, "已匹配(合併)")
                    i += 1
            else:
                # 正常情況，直接加入
                refined.append((ch_curr, ts_curr, status))
                i += 1
                
        return refined


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
