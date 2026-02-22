import numpy as np
import re
import json
import pandas as pd
import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

file_path = os.path.dirname(os.path.abspath(__file__))

# --- 路徑設定 ---
# 請根據需求調整輸入輸出路徑
INPUT_FILE_PATH = os.path.join(file_path, 'Ailgn_syllables', 'aligned_syllables.json')
OUTPUT_FILE_PATH = os.path.join(file_path, 'output_alignment_refined.xlsx')
OUTPUT_JSON_PATH = os.path.join(file_path, 'output_alignment_refined.json') # 新增 JSON 輸出路徑

class PhoneticAligner:
    def __init__(self):
        # 定義聲母群組 (用於模糊比對聲母相似度)
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
        
        # 定義正規化映射 (處理 w/u, y/i 的互通性)
        self.vowel_map = {'w': 'u', 'y': 'i'}

    def calculate_consonant_score(self, c_ch, c_ts):
        """計算聲母相似度分數"""
        # 0c 代表無聲母
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
        """
        計算 Dice Coefficient 相似度
        Dice: 2 * LCS(s1, s2) / (|s1| + |s2|)
        使用 LCS (最長公共子序列) 演算法計算 intersection
        """
        # 0v 代表無韻母
        if s1 == "0v" and s2 == "0v": return 1.0
        if s1 == "0v" or s2 == "0v": return 0.0
        
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
        """計算兩個音節的總相似度 (聲母 + 韻母)"""
        # 聲母分數 (initial)
        score_initial = self.calculate_consonant_score(syl_ch['initial'], syl_in['initial']) * 1
        # 韻母分數 (final)
        score_final = self.dice_coefficient(syl_ch['final'], syl_in['final']) * 1
        
        return score_initial + score_final

    def align(self, ch_syllables, in_syllables):
        """
        Needleman-Wunsch 全局對齊演算法
        """
        n = len(ch_syllables)
        m = len(in_syllables)
        gap_penalty = 0 
        
        dp = np.zeros((n + 1, m + 1))
        # 初始化路徑矩陣
        dir_matrix = [["" for _ in range(m + 1)] for _ in range(n + 1)]
        
        # 初始化邊界條件 (Gap Penalty 累積)
        for i in range(1, n + 1):
            dp[i][0] = dp[i-1][0] + gap_penalty
            dir_matrix[i][0] = "↑"
        for j in range(1, m + 1):
            dp[0][j] = dp[0][j-1] + gap_penalty
            dir_matrix[0][j] = "←"
            
        # 填滿 DP 表格
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
        
        # 回溯 (Backtracking) 產生對齊路徑
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
        """合併兩個音節"""
        append_initial = syl_append['initial']    
        # if append_initial == '0c': append_initial = ''
        
        # 合併邏輯：原音節的 final + 孤兒音節的 initial + 孤兒音節的 final
        new_final = syl_base['final'] + append_initial + syl_append['final']
        new_pinyin = syl_base.get('pinyin', '') + syl_append.get('pinyin', '')
        
        return {
            'initial': syl_base['initial'],
            'final': new_final,
            'pinyin': new_pinyin
        }

    def refine_alignment(self, original_alignment):
        """
        多次迴圈合併版 (Iterative Merge)
        邏輯：針對每一個「中文缺失」(多餘族語)，計算「併入左邊」vs「併入右邊」的分數差，
        選擇最佳的一邊進行合併，直到無法再優化為止。
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
                        new_alignment[-1] = (new_alignment[-1][0], merged_left_ts, "已匹配(合併)")
                        has_changed = True
                        i += 1 # 當前 orphan 已經被吸收到左邊了，跳過
                    else:
                        # ✅ 向右合併勝出
                        # 我們修改 current_alignment[i+1]，讓 orphan 被吸收到下一個格子裡
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
    """
    解析拼音字串，例如 's,e' -> initial='s', final='e'
    改名對照: onset->initial, rhyme->final, raw->pinyin
    """
    if not pinyin_str:
        return {'initial': '', 'final': '', 'pinyin': ''}
    
    parts = pinyin_str.split(',')
    if len(parts) == 2:
        initial, final = parts[0].strip(), parts[1].strip()
    else:
        initial, final = "", pinyin_str.strip()
        
    return {
        'initial': initial,
        'final': final,
        'pinyin': initial + final
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
    
    # 用來儲存所有詞彙的 JSON 結果列表
    json_results = []

    print(f"正在處理 {len(data)} 筆資料...")
    
    # --- 定義一個內部小函式來清理 0c 和 0v ---
    def clean_syllable_data(syl_dict):
        """移除音節資料中的 0c 和 0v 標記 (key 已更新為 initial/final/pinyin)"""
        if not syl_dict:
            return None
        # 建立副本以避免修改到原始參照
        new_dict = syl_dict.copy()
        new_dict['initial'] = new_dict['initial'].replace("0c", "").replace("0v", "")
        new_dict['final'] = new_dict['final'].replace("0c", "").replace("0v", "")
        new_dict['pinyin'] = new_dict['pinyin'].replace("0c", "").replace("0v", "")
        return new_dict

    for entry in data:
        raw_dict_pinyin = entry.get('dict_pinyin', [])
        raw_pinyin_info = entry.get('pinyin_info', [])
        
        ch_input = [parse_pinyin_string(s) for s in raw_dict_pinyin]
        ts_input = [parse_pinyin_string(s) for s in raw_pinyin_info]

        # 1. 執行 Needleman-Wunsch 對齊 (產生矩陣)
        alignment_result, dp_matrix, dir_matrix, path_coords = aligner.align(ch_input, ts_input)
        
        # 2. 執行 Refine (合併孤兒音節)
        final_alignment = aligner.refine_alignment(alignment_result)
        
        # --- 收集 JSON 資料 ---
        aligned_syllables_data = []
        
        # --- 準備 Excel 資料 ---
        aligned_pairs = ["|"]
        status_list = []
        details_list = []
        
        for ch, ts, status in final_alignment:
            # --- 1. Excel 顯示處理 (原本的邏輯，保持不變，單純為了視覺化) ---
            # 使用新的 key: pinyin 代替 raw
            c_str = ch['pinyin'] if ch else "---"
            t_str = ts['pinyin'] if ts else "---"
            c_str = c_str.replace("0c", "").replace("0v", "")  # 移除 '0c' 表示的無聲母
            t_str = t_str.replace("0c", "").replace("0v", "")
            
            aligned_pairs.append(f"{c_str} ↔ {t_str} | ")
            status_list.append(status)
            
            if ch and ts:
                # 使用新的 key: initial, final
                onset_score = aligner.calculate_consonant_score(ch['initial'], ts['initial'])
                dice_score = aligner.dice_coefficient(ch['final'], ts['final'])
                details_list.append(f"聲:{'Yes' if onset_score>0 else 'No'} | 韻:{dice_score:.2f}")
            else:
                details_list.append("---")
            
            # --- 2. JSON 資料結構處理 ---
            # 新增邏輯：如果是匹配狀態，移除 0c/0v
            ch_data = ch
            ts_data = ts

            if status in ["已匹配", "已匹配(合併)"]:
                ch_data = clean_syllable_data(ch)
                ts_data = clean_syllable_data(ts)

            syllable_entry = {
                "status": status,
                # 如果 ch 或 ts 是 None (例如缺失)，在 JSON 裡存為 null
                "chinese_syllable": ch_data if ch_data else None,
                "tsou_syllable": ts_data if ts_data else None
            }
            aligned_syllables_data.append(syllable_entry)

        # 將此詞彙的完整結果加入列表
        json_results.append({
            "chinese": entry.get('chinese', ''),
            "ch_semantic": entry.get('ch_semantic', ''),
            "original_pinyin_ch": raw_dict_pinyin,
            "original_pinyin_ts": raw_pinyin_info,
            "alignment": aligned_syllables_data
        })

        # --- 寫入 Excel Sheet 1 ---
        ws_summary.append([
            entry.get('chinese', ''),
            entry.get('ch_semantic', ''),
            "-".join([str(s) if s else "" for s in raw_dict_pinyin]),
            "-".join([str(s) if s else "" for s in raw_pinyin_info]),
            "\n".join(aligned_pairs),
            ", ".join(status_list),
            "\n".join(details_list)
        ])

        # --- 寫入 Excel Sheet 2 (矩陣視覺化) ---
        ws_matrix.cell(row=current_matrix_row, column=1, value=f"詞彙: {entry.get('chinese', '')}")
        ws_matrix.cell(row=current_matrix_row, column=1).font = Font(bold=True, size=12)
        current_matrix_row += 1

        # 使用新的 key: pinyin 作為表頭
        row_headers = ["Start"] + [x['pinyin'] for x in ch_input]
        col_headers = ["Start"] + [x['pinyin'] for x in ts_input]

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

    # 自動調整 Excel 欄寬
    for col in ws_summary.columns:
        length = max(len(str(cell.value)) for cell in col)
        ws_summary.column_dimensions[get_column_letter(col[0].column)].width = min(length + 2, 50)

    # 儲存 Excel
    try:
        wb.save(output_excel_path)
        print(f"✅ Excel 處理完成！結果已儲存至: {output_excel_path}")
    except Exception as e:
        print(f"❌ Excel 儲存失敗 (請檢查檔案是否被開啟): {e}")

    # 儲存 JSON
    try:
        # ensure_ascii=False 確保中文字元能正確顯示，而不是顯示 unicode 編碼
        with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, ensure_ascii=False, indent=4)
        print(f"✅ JSON 處理完成！結果已儲存至: {OUTPUT_JSON_PATH}")
    except Exception as e:
        print(f"❌ JSON 儲存失敗: {e}")

if __name__ == "__main__":
    process_json_to_excel(INPUT_FILE_PATH, OUTPUT_FILE_PATH)