import json
import os
import sys
import glob
import pandas as pd

# ==========================================
# 1. 動態引入其他資料夾的模組
# ==========================================
# 取得目前 LOOCV.py 所在的絕對路徑目錄
current_dir = os.path.dirname(os.path.abspath(__file__))

MODULE_DIR = os.path.abspath(os.path.join(current_dir, "Ailgn_syllables")) 

# 將該路徑加入 Python 的搜尋路徑中
if MODULE_DIR not in sys.path:
    sys.path.append(MODULE_DIR)

import Align_syllables03


def get_best_phoneme(ch_phoneme, vote_data, word_deductions):
    """
    動態計算扣除該詞發音後的最佳推薦音
    """
    if ch_phoneme not in vote_data or not vote_data[ch_phoneme]:
        return None

    candidates = vote_data[ch_phoneme]
    best_tgt = None
    best_score = -1
    best_global = -1

    for tgt_phoneme, stats in candidates.items():
        original_count = stats.get("local_count", 0)
        
        deduct = 0
        if ch_phoneme in word_deductions and tgt_phoneme in word_deductions[ch_phoneme]:
            deduct = word_deductions[ch_phoneme][tgt_phoneme]

        adj_count = max(0, original_count - deduct)
        global_score = stats.get("global_score_i", 0.0)

        if adj_count > best_score:
            best_score = adj_count
            best_global = global_score
            best_tgt = tgt_phoneme
        elif adj_count == best_score:
            if global_score > best_global:
                best_global = global_score
                best_tgt = tgt_phoneme

    return best_tgt

def process_word_level_loocv(refined_dir, vote_dir, output_excel_path, ch_dict, cedict_index):
    refined_pattern = os.path.join(refined_dir, "refined_*.json")
    refined_files = glob.glob(refined_pattern)
    
    if not refined_files:
        print(f"⚠️ 警告：在 {refined_dir} 找不到任何 refined_*.json 檔案，請檢查路徑是否正確。")
        return

    all_results = []
    global_total = 0
    global_correct = 0
    language_stats = {}  
    
    for refined_file in refined_files:
        base_name = os.path.basename(refined_file)
        parts = base_name.split('_')
        prefix_num = parts[1] if len(parts) > 1 else "Unknown"
        lang_name = parts[2].replace(".json", "") if len(parts) > 2 else f"Language_{prefix_num}"
        
        lang_key = f"{prefix_num}_{lang_name}"
        
        if lang_key not in language_stats:
            language_stats[lang_key] = {"total": 0, "correct": 0}
            
        vote_file = os.path.join(vote_dir, f"{prefix_num}_output_alignment_voted.json")
        
        if not os.path.exists(vote_file):
            print(f"⚠️ 找不到對應的 Vote 檔案: {vote_file}，略過 {base_name}")
            continue
            
        with open(refined_file, 'r', encoding='utf-8') as f:
            refined_data = json.load(f)
            
        with open(vote_file, 'r', encoding='utf-8') as f:
            vote_data = json.load(f)
            
        for entry in refined_data:
            word = entry.get("chinese", "")
            alignment = entry.get("alignment", [])
            
            # 呼叫 Align_syllables03 動態拆解該詞彙
            dynamic_alignment_result = Align_syllables03.align_word_to_initial_final(word, ch_dict, cedict_index)
            char_alignments = dynamic_alignment_result.get("char_alignment", [])
            
            # 防呆：確保動態拆解出來的字數與標註檔案中的字數一致
            if len(char_alignments) != len(alignment):
                print(f"⚠️ 字數不匹配跳過: '{word}' (動態:{len(char_alignments)}字 vs 標註:{len(alignment)}字)")
                continue

            word_deductions = {}
            for dyn_char, align in zip(char_alignments, alignment):
                ch_ini = dyn_char.get("initial", "0c")
                ch_fin = dyn_char.get("final", "0v")
                
                gt_ini = align.get("tsou_syllable", {}).get("initial", "") or "0c"
                gt_fin = align.get("tsou_syllable", {}).get("final", "") or "0v"
                
                if ch_ini not in word_deductions: word_deductions[ch_ini] = {}
                word_deductions[ch_ini][gt_ini] = word_deductions[ch_ini].get(gt_ini, 0) + 1
                
                if ch_fin not in word_deductions: word_deductions[ch_fin] = {}
                word_deductions[ch_fin][gt_fin] = word_deductions[ch_fin].get(gt_fin, 0) + 1

            word_is_correct = True
            process_details = []
            
            for dyn_char, align in zip(char_alignments, alignment):
                ch_ini = dyn_char.get("initial", "0c")
                ch_fin = dyn_char.get("final", "0v")
                
                gt_ini = align.get("tsou_syllable", {}).get("initial", "") or "0c"
                gt_fin = align.get("tsou_syllable", {}).get("final", "") or "0v"
                
                pred_ini = get_best_phoneme(ch_ini, vote_data, word_deductions)
                pred_fin = get_best_phoneme(ch_fin, vote_data, word_deductions)
                
                pred_ini = pred_ini if pred_ini is not None else "N/A"
                pred_fin = pred_fin if pred_fin is not None else "N/A"
                
                ini_correct = (pred_ini == gt_ini)
                fin_correct = (pred_fin == gt_fin)
                
                if not ini_correct or not fin_correct:
                    word_is_correct = False
                    
                detail = (f"中({ch_ini},{ch_fin}) -> "
                          f"預測({pred_ini},{pred_fin}) | "
                          f"解答({gt_ini},{gt_fin})")
                process_details.append(detail)
                
            global_total += 1
            language_stats[lang_key]["total"] += 1
            
            if word_is_correct:
                global_correct += 1
                language_stats[lang_key]["correct"] += 1
                
            all_results.append({
                "族語": lang_key,
                "中文詞彙": word,
                "測試過程與比對": "\n".join(process_details),
                "是否完全正確": "是" if word_is_correct else "否"
            })

    if global_total == 0:
        print("❌ 沒有成功處理任何資料，請檢查資料夾路徑與檔案名稱格式是否正確。")
        return

    stats_rows = []
    for lang_key, stats in language_stats.items():
        t = stats["total"]
        c = stats["correct"]
        acc = c / t if t > 0 else 0
        stats_rows.append({
            "族語名稱": lang_key,
            "總測試詞數": t,
            "完全正確詞數": c,
            "正確率": f"{acc:.2%}"
        })
        
    global_acc = global_correct / global_total if global_total > 0 else 0
    stats_rows.append({
        "族語名稱": "【整體總計】",
        "總測試詞數": global_total,
        "完全正確詞數": global_correct,
        "正確率": f"{global_acc:.2%}"
    })
    
    df_stats = pd.DataFrame(stats_rows)
    df_details = pd.DataFrame(all_results)
    
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        df_stats.to_excel(writer, sheet_name="正確率統計", index=False)
        df_details.to_excel(writer, sheet_name="詳細結果", index=False)
        
    print(f"✅ 已成功匯出 Word-Level LOO 測試結果至: {output_excel_path}")
    print(f"✅ 整體總正確率為: {global_acc:.2%}")

if __name__ == "__main__":
    # ==========================================
    # 2. 設定資料夾與檔案相對路徑
    # ==========================================
    # 以下請依照 LOOCV.py 所在的相對位置來設定
    REFINED_DIR = "Refined_Excel/"      
    VOTE_DIR = "vote_result/"             
    OUTPUT_FILE = "LOO_WordLevel_Validation_Results.xlsx" 
    
    # 假設字典檔跟模組放在同一個目錄 (MODULE_DIR)
    DICT_FILENAME = os.path.join(MODULE_DIR, "ch_dict.json")
    CEDICT_FILENAME = os.path.join(MODULE_DIR, "cedict_normalized.json")
    
    print(f"📖 正在從 {MODULE_DIR} 載入字典...")
    try:
        with open(DICT_FILENAME, "r", encoding="utf-8") as f:
            ch_dict = json.load(f)
        with open(CEDICT_FILENAME, "r", encoding="utf-8") as f:
            cedict_data = json.load(f)
        
        cedict_index = Align_syllables03.build_cedict_index(cedict_data)
        print("✅ 字典載入完成！")
    except Exception as e:
        print(f"❌ 讀取字典失敗，請確認檔案路徑是否正確: {e}")
        exit()

    print(f"準備讀取 Refined 資料夾: {REFINED_DIR}")
    print(f"準備讀取 Vote 資料夾: {VOTE_DIR}")
    
    process_word_level_loocv(REFINED_DIR, VOTE_DIR, OUTPUT_FILE, ch_dict, cedict_index)