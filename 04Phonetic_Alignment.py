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
INPUT_FILE_PATH = os.path.join(file_path, 'Ailgn_syllables', 'aligned_syllables.json')
OUTPUT_FILE_PATH = os.path.join(file_path, 'output_alignment_refined.xlsx')
OUTPUT_JSON_PATH = os.path.join(file_path, 'output_alignment_refined.json') # 新增 JSON 輸出路徑

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
        score_onset = self.calculate_consonant_score(syl_ch['onset'], syl_in['onset']) * 1
        score_rhyme = self.dice_coefficient(syl_ch['rhyme'], syl_in['rhyme']) * 1
        return score_onset + score_rhyme

    def align(self, ch_syllables, in_syllables):
        n = len(ch_syllables)
        m = len(in_syllables)
        gap_penalty = 0 
        dp = np.zeros((n + 1, m + 1))
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
                if best_score == match: dir_matrix[i][j] = "↖"
                elif best_score == delete: dir_matrix[i][j] = "↑"
                else: dir_matrix[i][j] = "←"
                
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
        new_rhyme = syl_base['rhyme'] + append_onset + syl_append['rhyme']
        new_raw = syl_base.get('raw', '') + syl_append.get('raw', '')
        return {'onset': syl_base['onset'], 'rhyme': new_rhyme, 'raw': new_raw}

    def refine_alignment(self, original_alignment):
        current_alignment = original_alignment
        while True:
            has_changed = False
            new_alignment = []
            n = len(current_alignment)
            i = 0
            while i < n:
                ch_curr, ts_curr, status = current_alignment[i]
                if status == "中文缺失" and ts_curr is not None:
                    orphan = ts_curr
                    delta_left = -float('inf')
                    merged_left_ts = None
                    delta_right = -float('inf')
                    merged_right_ts = None
                    
                    if len(new_alignment) > 0 and new_alignment[-1][2] in ["已匹配", "已匹配(合併)"]:
                        prev_ch = new_alignment[-1][0]
                        prev_ts = new_alignment[-1][1]
                        score_orig = self.calculate_similarity(prev_ch, prev_ts)
                        temp_merged = self.merge_syllables(prev_ts, orphan)
                        score_new = self.calculate_similarity(prev_ch, temp_merged)
                        delta_left = score_new - score_orig
                        merged_left_ts = temp_merged
                        
                    if i + 1 < n and current_alignment[i+1][2] in ["已匹配", "已匹配(合併)"]:
                        next_ch = current_alignment[i+1][0]
                        next_ts = current_alignment[i+1][1]
                        score_orig = self.calculate_similarity(next_ch, next_ts)
                        temp_merged = self.merge_syllables(orphan, next_ts)
                        score_new = self.calculate_similarity(next_ch, temp_merged)
                        delta_right = score_new - score_orig
                        merged_right_ts = temp_merged
                    
                    if delta_left == -float('inf') and delta_right == -float('inf'):
                        new_alignment.append((ch_curr, ts_curr, status))
                        i += 1
                        continue
                        
                    if delta_left >= delta_right:
                        new_alignment[-1] = (new_alignment[-1][0], merged_left_ts, "已匹配(合併)")
                        has_changed = True
                        i += 1 
                    else:
                        target_next = current_alignment[i+1]
                        current_alignment[i+1] = (target_next[0], merged_right_ts, "已匹配(合併)")
                        has_changed = True
                        i += 1 
                else:
                    new_alignment.append((ch_curr, ts_curr, status))
                    i += 1
            current_alignment = new_alignment
            if not has_changed: break
        return current_alignment

def parse_pinyin_string(pinyin_str):
    if not pinyin_str: return {'onset': '', 'rhyme': '', 'raw': ''}
    parts = pinyin_str.split(',')
    if len(parts) == 2: onset, rhyme = parts[0].strip(), parts[1].strip()
    else: onset, rhyme = "", pinyin_str.strip()
    return {'onset': onset, 'rhyme': rhyme, 'raw': onset + rhyme}

def process_json_to_excel(json_file_path, output_excel_path):
    if not os.path.exists(json_file_path):
        print(f"找不到檔案 {json_file_path}，使用範例資料...")
        data = [{"chinese": "範例詞", "ch_semantic": "測試", "pinyin_info": ["s,e", "w,a", "k,a"], "dict_pinyin": ["sh,ua", "k,a"]}]
    else:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

    aligner = PhoneticAligner()
    wb = Workbook()
    
    ws_summary = wb.active
    ws_summary.title = "對齊結果列表"
    ws_summary.append(["詞彙", "語意", "標準拼音", "實際拼音", "對齊視覺化", "狀態", "詳細分數"])
    ws_matrix = wb.create_sheet("矩陣視覺化")
    
    red_bold_font = Font(color="FF0000", bold=True)
    highlight_fill = PatternFill(start_color="FFFFCC", end_color="FFFFCC", fill_type="solid")
    center_align = Alignment(horizontal='center', vertical='center')
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    current_matrix_row = 1
    
    # 用來儲存所有詞彙的 JSON 結果列表
    json_results = []

    print(f"正在處理 {len(data)} 筆資料...")
    
    # 定義一個內部小函式來清理 0c 和 0v
    def clean_syllable_data(syl_dict):
        if not syl_dict:
            return None
        # 建立副本以避免修改到原始參照 (雖然在此情境下直接改也無妨，但安全起見)
        new_dict = syl_dict.copy()
        new_dict['onset'] = new_dict['onset'].replace("0c", "").replace("0v", "")
        new_dict['rhyme'] = new_dict['rhyme'].replace("0c", "").replace("0v", "")
        new_dict['raw'] = new_dict['raw'].replace("0c", "").replace("0v", "")
        return new_dict

    for entry in data:
        raw_dict_pinyin = entry.get('dict_pinyin', [])
        raw_pinyin_info = entry.get('pinyin_info', [])
        
        ch_input = [parse_pinyin_string(s) for s in raw_dict_pinyin]
        ts_input = [parse_pinyin_string(s) for s in raw_pinyin_info]

        alignment_result, dp_matrix, dir_matrix, path_coords = aligner.align(ch_input, ts_input)
        final_alignment = aligner.refine_alignment(alignment_result)
        
        # --- 收集 JSON 資料 ---
        aligned_syllables_data = []
        
        # --- 準備 Excel 資料 ---
        aligned_pairs = ["|"]
        status_list = []
        details_list = []
        
        for ch, ts, status in final_alignment:
            # 1. Excel 顯示處理 (原本的邏輯，保持不變)
            c_str = ch['raw'] if ch else "---"
            t_str = ts['raw'] if ts else "---"
            c_str = c_str.replace("0c", "").replace("0v", "")
            t_str = t_str.replace("0c", "").replace("0v", "")
            
            aligned_pairs.append(f"{c_str} ↔ {t_str} | ")
            status_list.append(status)
            
            if ch and ts:
                onset_score = aligner.calculate_consonant_score(ch['onset'], ts['onset'])
                dice_score = aligner.dice_coefficient(ch['rhyme'], ts['rhyme'])
                details_list.append(f"聲:{'Yes' if onset_score>0 else 'No'} | 韻:{dice_score:.2f}")
            else:
                details_list.append("---")
            
            # 2. JSON 資料結構處理 (新增邏輯：如果是匹配狀態，移除 0c/0v)
            ch_data = ch
            ts_data = ts

            if status in ["已匹配", "已匹配(合併)"]:
                ch_data = clean_syllable_data(ch)
                ts_data = clean_syllable_data(ts)

            syllable_entry = {
                "status": status,
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

        ws_summary.append([
            entry.get('chinese', ''),
            entry.get('ch_semantic', ''),
            "-".join([str(s) if s else "" for s in raw_dict_pinyin]),
            "-".join([str(s) if s else "" for s in raw_pinyin_info]),
            "\n".join(aligned_pairs),
            ", ".join(status_list),
            "\n".join(details_list)
        ])

        # --- Matrix Sheet (保持不變) ---
        ws_matrix.cell(row=current_matrix_row, column=1, value=f"詞彙: {entry.get('chinese', '')}").font = Font(bold=True, size=12)
        current_matrix_row += 1
        row_headers = ["Start"] + [x['raw'] for x in ch_input]
        col_headers = ["Start"] + [x['raw'] for x in ts_input]
        start_col_idx = 2
        for idx, text in enumerate(col_headers):
            cell = ws_matrix.cell(row=current_matrix_row, column=start_col_idx + idx, value=text)
            cell.alignment = center_align; cell.font = Font(bold=True); cell.border = thin_border
        current_matrix_row += 1
        n_rows, m_cols = dp_matrix.shape
        for i in range(n_rows):
            ws_matrix.cell(row=current_matrix_row + i, column=1, value=row_headers[i]).font = Font(bold=True)
            ws_matrix.cell(row=current_matrix_row + i, column=1).border = thin_border
            for j in range(m_cols):
                val = dp_matrix[i][j]; direction = dir_matrix[i][j]
                cell = ws_matrix.cell(row=current_matrix_row + i, column=start_col_idx + j, value=f"{direction} {val:.2f}" if direction else f"{val:.2f}")
                cell.alignment = center_align; cell.border = thin_border
                if (i, j) in path_coords: cell.font = red_bold_font; cell.fill = highlight_fill
        current_matrix_row += n_rows + 2

    for col in ws_summary.columns:
        ws_summary.column_dimensions[get_column_letter(col[0].column)].width = min(max(len(str(cell.value)) for cell in col) + 2, 50)

    # 儲存 Excel
    try:
        wb.save(output_excel_path)
        print(f"✅ Excel 處理完成！結果已儲存至: {output_excel_path}")
    except Exception as e:
        print(f"❌ Excel 儲存失敗: {e}")

    # 儲存 JSON
    try:
        # 新增參數 ensure_ascii=False 讓中文正常顯示
        with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(json_results, f, ensure_ascii=False, indent=4)
        print(f"✅ JSON 處理完成！結果已儲存至: {OUTPUT_JSON_PATH}")
    except Exception as e:
        print(f"❌ JSON 儲存失敗: {e}")
        
if __name__ == "__main__":
    process_json_to_excel(INPUT_FILE_PATH, OUTPUT_FILE_PATH)