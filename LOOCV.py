import json
import os
import sys
import glob
import pandas as pd

# 引入查詢音節數量的工具
# 假設您的資料夾結構是 fm_dict/get_syllable_count.py 或同層級的 syllable_tool.py
# 請依據實際情況調整 import，這裡沿用您原本檔案的寫法
try:
    from fm_dict.get_syllable_count import get_syllable_count, get_raw_string_count
except ImportError:
    # 如果找不到 fm_dict，嘗試直接引入 (視您的檔案擺放位置而定)
    try:
        import get_syllable_count as tool_module 
        
        get_syllable_count = tool_module.get_syllable_count
        get_raw_string_count = tool_module.get_raw_string_count
    except ImportError:
        print("⚠️ 警告：找不到 get_syllable_count 函式，請確認檔案位置。")
        # 定義一個 dummy function 避免程式崩潰
        def get_syllable_count(s, l): return 0

# ==========================================
# 1. 動態引入其他資料夾的模組
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.abspath(os.path.join(current_dir, "Ailgn_syllables")) 

if MODULE_DIR not in sys.path:
    sys.path.append(MODULE_DIR)

import Align_syllables03


def get_top3_phonemes(ch_phoneme, vote_data, word_deductions, language_name):
    """
    動態計算扣除該詞發音後的所有候選音，並回傳排序後的前三名。
    
    排序邏輯 (由高到低):
    1. adj_count (LOO 調整後票數)
    2. dict_count (該音節在字典中的總出現次數) -> 新增規則
    3. global_score (全域分數)
    """
    if ch_phoneme not in vote_data or not vote_data[ch_phoneme]:
        return []

    candidates = vote_data[ch_phoneme]
    scored_candidates = []

    for tgt_phoneme, stats in candidates.items():
        original_count = stats.get("local_count", 0)
        
        # 查詢扣除數
        deduct = 0
        if ch_phoneme in word_deductions and tgt_phoneme in word_deductions[ch_phoneme]:
            deduct = word_deductions[ch_phoneme][tgt_phoneme]

        # 1. 計算 LOO 票數
        adj_count = max(0, original_count - deduct)
        
        # 2. 查詢字典出現次數 (新增邏輯)
        dict_count = get_raw_string_count(tgt_phoneme, language_name)
        
        # 3. 取得 Global Score
        global_score = stats.get("global_score_i", 0.0)

        scored_candidates.append({
            "phoneme": tgt_phoneme,
            "original_count": original_count,
            "deduct": deduct,
            "adj_count": adj_count,
            "dict_count": dict_count,  # 記錄下來以便排序與顯示
            "global_score": global_score
        })

    # === 核心修改：更新排序規則 ===
    # Python 的 tuple 比較會依序比較元素：先比 adj_count，一樣則比 dict_count，再一樣比 global_score
    # 這裡依照您之前的要求：先比票數 -> 再比字典數 -> 最後比 Global 分數
    #scored_candidates.sort(key=lambda x: (x["adj_count"], x["dict_count"], x["global_score"]), reverse=True)
    scored_candidates.sort(key=lambda x: (x["adj_count"], x["global_score"], x["dict_count"]), reverse=True)

    return scored_candidates[:3]

def format_top3_display(top3_list):
    """
    將前三名格式化為文字，新增顯示「字典數量(D)」與「全域分數(G)」
    格式: p(10, D:50, G:0.23), m(10, D:20, G:0.15)
    """
    if not top3_list:
        return "N/A"
        
    formatted_items = []
    for item in top3_list:
        phoneme = item['phoneme']
        orig = item['original_count']
        deduct = item['deduct']
        adj = item['adj_count']
        dct = item['dict_count']
        glob_score = item['global_score']
        
        # 顯示格式： 音節(LOO票數, D:字典數, G:全域分數)
        # 例如: ma(12-2=10, D:152, G:0.23)
        # G 分數取小數點後兩位
        formatted_items.append(f"{phoneme}({orig}-{deduct}={adj}, D:{dct}, G:{glob_score:.2f})")
        
    return ", ".join(formatted_items)

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
        # 取得語言名稱 (例如 Amis) 用於查詢字典統計
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
            
            # 動態拆解
            dynamic_alignment_result = Align_syllables03.align_word_to_initial_final(word, ch_dict, cedict_index)
            char_alignments = dynamic_alignment_result.get("char_alignment", [])
            
            if len(char_alignments) != len(alignment):
                print(f"⚠️ 字數不匹配跳過: '{word}'")
                continue

            # 統計該詞發音 (用於 LOO 扣除)
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
                
                # === 修改處：傳入 lang_name 以查詢字典統計 ===
                top3_ini = get_top3_phonemes(ch_ini, vote_data, word_deductions, lang_name)
                top3_fin = get_top3_phonemes(ch_fin, vote_data, word_deductions, lang_name)
                
                # 取第一名作為預測結果
                pred_ini_top1 = top3_ini[0]["phoneme"] if top3_ini else "N/A"
                pred_fin_top1 = top3_fin[0]["phoneme"] if top3_fin else "N/A"
                
                ini_correct = (pred_ini_top1 == gt_ini)
                fin_correct = (pred_fin_top1 == gt_fin)
                
                if not ini_correct or not fin_correct:
                    word_is_correct = False
                    
                str_top3_ini = format_top3_display(top3_ini)
                str_top3_fin = format_top3_display(top3_fin)
                
                detail = (f"中({ch_ini},{ch_fin}) -> "
                          f"預測:[{str_top3_ini}] | [{str_top3_fin}] | "
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
                "是否完全正確": "是" if word_is_correct else "否",
                "測試過程與比對": "\n".join(process_details)
            })

    if global_total == 0:
        print("❌ 沒有成功處理任何資料。")
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
        
    print(f"✅ 已成功匯出結果至: {output_excel_path}")
    print(f"✅ 整體總正確率為: {global_acc:.2%}")

if __name__ == "__main__":
    # 路徑設定
    REFINED_DIR = os.path.join(current_dir, "Refined_Excel/")     
    VOTE_DIR = os.path.join(current_dir, "vote_result/")      
    OUTPUT_FILE = os.path.join(current_dir, "LOOCV_Results.xlsx") 
    
    DICT_FILENAME = os.path.join(MODULE_DIR, "ch_dict.json")
    CEDICT_FILENAME = os.path.join(MODULE_DIR, "cedict_normalized.json")
    
    print(f"📖 載入字典中...")
    try:
        with open(DICT_FILENAME, "r", encoding="utf-8") as f:
            ch_dict = json.load(f)
        with open(CEDICT_FILENAME, "r", encoding="utf-8") as f:
            cedict_data = json.load(f)
        cedict_index = Align_syllables03.build_cedict_index(cedict_data)
        print("✅ 字典載入完成！")
    except Exception as e:
        print(f"❌ 字典讀取失敗: {e}")
        exit()

    process_word_level_loocv(REFINED_DIR, VOTE_DIR, OUTPUT_FILE, ch_dict, cedict_index)
