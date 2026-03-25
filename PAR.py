import json
import os
import sys
import glob
import pandas as pd

# 引入查詢音節數量的工具
try:
    from fm_dict.get_syllable_count import get_syllable_count, get_raw_string_count
except ImportError:
    try:
        import get_syllable_count as tool_module 
        get_syllable_count = tool_module.get_syllable_count
        get_raw_string_count = tool_module.get_raw_string_count
    except ImportError:
        print("⚠️ 警告：找不到 get_syllable_count 函式，請確認檔案位置。")
        def get_syllable_count(s, l): return 0
        def get_raw_string_count(s, l): return 0

# ==========================================
# 動態引入其他資料夾的模組
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
MODULE_DIR = os.path.abspath(os.path.join(current_dir, "Ailgn_syllables")) 

if MODULE_DIR not in sys.path:
    sys.path.append(MODULE_DIR)

import Align_syllables03

def get_top3_phonemes(ch_phoneme, vote_data, word_deductions, language_name):
    """取得扣減同詞發音後的預測結果 (LOO)"""
    if ch_phoneme not in vote_data or not vote_data[ch_phoneme]:
        return []

    candidates = vote_data[ch_phoneme]
    scored_candidates = []

    for tgt_phoneme, stats in candidates.items():
        original_count = stats.get("local_count", 0)
        deduct = 0
        if ch_phoneme in word_deductions and tgt_phoneme in word_deductions[ch_phoneme]:
            deduct = word_deductions[ch_phoneme][tgt_phoneme]

        adj_count = max(0, original_count - deduct)
        dict_count = get_raw_string_count(tgt_phoneme, language_name)
        global_score = stats.get("global_score_i", 0.0)

        scored_candidates.append({
            "phoneme": tgt_phoneme,
            "adj_count": adj_count,
            "dict_count": dict_count,
            "global_score": global_score
        })

    scored_candidates.sort(key=lambda x: (x["adj_count"], x["global_score"], x["dict_count"]), reverse=True)
    return scored_candidates[:3]


def analyze_phoneme_accuracy(refined_dir, vote_dir, output_excel_path, ch_dict, cedict_index):
    refined_pattern = os.path.join(refined_dir, "refined_*.json")
    refined_files = glob.glob(refined_pattern)
    
    if not refined_files:
        print(f"⚠️ 警告：在 {refined_dir} 找不到任何 refined_*.json 檔案。")
        return

    language_stats = {}  
    # 🌟 新增「完整音節」分類，追蹤聲母+韻母合體的狀態
    phoneme_details = {"聲母": {}, "韻母": {}, "完整音節": {}}

    global_total_syllables = 0
    global_ini_correct = 0
    global_fin_correct = 0
    global_full_syll_correct = 0

    for refined_file in refined_files:
        base_name = os.path.basename(refined_file)
        parts = base_name.split('_')
        prefix_num = parts[1] if len(parts) > 1 else "Unknown"
        lang_name = parts[2].replace(".json", "") if len(parts) > 2 else f"Language_{prefix_num}"
        lang_key = f"{prefix_num}_{lang_name}"
        
        if lang_key not in language_stats:
            language_stats[lang_key] = {
                "total_syllables": 0, 
                "ini_correct": 0, 
                "fin_correct": 0, 
                "full_syll_correct": 0
            }
            phoneme_details["聲母"][lang_key] = {}
            phoneme_details["韻母"][lang_key] = {}
            phoneme_details["完整音節"][lang_key] = {}
            
        vote_file = os.path.join(vote_dir, f"{prefix_num}_output_alignment_voted.json")
        if not os.path.exists(vote_file):
            continue
            
        with open(refined_file, 'r', encoding='utf-8') as f:
            refined_data = json.load(f)
        with open(vote_file, 'r', encoding='utf-8') as f:
            vote_data = json.load(f)
            
        for entry in refined_data:
            word = str(entry.get("chinese", ""))
            alignment = entry.get("alignment", [])
            
            dynamic_alignment_result = Align_syllables03.align_word_to_initial_final(word, ch_dict, cedict_index)
            char_alignments = dynamic_alignment_result.get("char_alignment", [])
            
            if len(char_alignments) != len(alignment):
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

            for dyn_char, align in zip(char_alignments, alignment):
                ch_ini = dyn_char.get("initial", "0c")
                ch_fin = dyn_char.get("final", "0v")
                
                gt_ini = align.get("tsou_syllable", {}).get("initial", "") or "0c"
                gt_fin = align.get("tsou_syllable", {}).get("final", "") or "0v"
                
                top3_ini = get_top3_phonemes(ch_ini, vote_data, word_deductions, lang_name)
                top3_fin = get_top3_phonemes(ch_fin, vote_data, word_deductions, lang_name)
                
                pred_ini = top3_ini[0]["phoneme"] if top3_ini else "N/A"
                pred_fin = top3_fin[0]["phoneme"] if top3_fin else "N/A"
                
                # ==========================================
                # 🌟 這裡就是拿「預測族語」跟「解答族語」直接比對
                # ==========================================
                is_ini_correct = (pred_ini.lower() == gt_ini.lower())
                is_fin_correct = (pred_fin.lower() == gt_fin.lower())
                is_syll_correct = is_ini_correct and is_fin_correct
                
                global_total_syllables += 1
                language_stats[lang_key]["total_syllables"] += 1
                
                if is_ini_correct:
                    global_ini_correct += 1
                    language_stats[lang_key]["ini_correct"] += 1
                if is_fin_correct:
                    global_fin_correct += 1
                    language_stats[lang_key]["fin_correct"] += 1
                if is_syll_correct:
                    global_full_syll_correct += 1
                    language_stats[lang_key]["full_syll_correct"] += 1
                    
                # 🌟 記錄時，把「中文發音」與「族語標準答案」綁定在一起做為 Key
                ini_key = (ch_ini, gt_ini)
                if ini_key not in phoneme_details["聲母"][lang_key]:
                    phoneme_details["聲母"][lang_key][ini_key] = {"total": 0, "correct": 0, "error_words": set()}
                phoneme_details["聲母"][lang_key][ini_key]["total"] += 1
                
                if is_ini_correct:
                    phoneme_details["聲母"][lang_key][ini_key]["correct"] += 1
                else:
                    phoneme_details["聲母"][lang_key][ini_key]["error_words"].add(word)
                    
                fin_key = (ch_fin, gt_fin)
                if fin_key not in phoneme_details["韻母"][lang_key]:
                    phoneme_details["韻母"][lang_key][fin_key] = {"total": 0, "correct": 0, "error_words": set()}
                phoneme_details["韻母"][lang_key][fin_key]["total"] += 1
                
                if is_fin_correct:
                    phoneme_details["韻母"][lang_key][fin_key]["correct"] += 1
                else:
                    phoneme_details["韻母"][lang_key][fin_key]["error_words"].add(word)

                # 🌟 新增：完整音節追蹤 (例如 l+ian -> l+in)
                ch_syll = f"{ch_ini}+{ch_fin}"
                gt_syll = f"{gt_ini}+{gt_fin}"
                syll_key = (ch_syll, gt_syll)
                if syll_key not in phoneme_details["完整音節"][lang_key]:
                    phoneme_details["完整音節"][lang_key][syll_key] = {"total": 0, "correct": 0, "error_words": set()}
                phoneme_details["完整音節"][lang_key][syll_key]["total"] += 1
                
                if is_syll_correct:
                    phoneme_details["完整音節"][lang_key][syll_key]["correct"] += 1
                else:
                    phoneme_details["完整音節"][lang_key][syll_key]["error_words"].add(word)

    # ==========================================
    # 產出 DataFrame
    # ==========================================
    if global_total_syllables == 0:
        print("❌ 沒有成功處理任何資料。")
        return

    # 表 1: 整體音節正確率
    summary_rows = []
    for lang_key, stats in language_stats.items():
        t = stats["total_syllables"]
        if t == 0: continue
        summary_rows.append({
            "族語名稱": lang_key,
            "總音節測試數": t,
            "聲母正確數": stats["ini_correct"],
            "聲母正確率": f"{stats['ini_correct']/t:.2%}",
            "韻母正確數": stats["fin_correct"],
            "韻母正確率": f"{stats['fin_correct']/t:.2%}",
            "完整音節正確數(聲+韻皆對)": stats["full_syll_correct"],
            "完整音節正確率": f"{stats['full_syll_correct']/t:.2%}",
        })
        
    summary_rows.append({
        "族語名稱": "【整體總計】",
        "總音節測試數": global_total_syllables,
        "聲母正確數": global_ini_correct,
        "聲母正確率": f"{global_ini_correct/global_total_syllables:.2%}",
        "韻母正確數": global_fin_correct,
        "韻母正確率": f"{global_fin_correct/global_total_syllables:.2%}",
        "完整音節正確數(聲+韻皆對)": global_full_syll_correct,
        "完整音節正確率": f"{global_full_syll_correct/global_total_syllables:.2%}",
    })
    df_summary = pd.DataFrame(summary_rows)

    # 表 2, 3, 4: 個別發音表現轉換為 DataFrame，加入「族語解答」對照
    def build_phoneme_df(phoneme_type):
        rows = []
        for lang_key, p_dict in phoneme_details[phoneme_type].items():
            for (ch_ph, gt_ph), stats in p_dict.items():
                t = stats["total"]
                c = stats["correct"]
                err_count = t - c
                
                if stats["error_words"]:
                    error_words_str = ", ".join(sorted(list(stats["error_words"])))
                    error_word_count = len(stats["error_words"])
                else:
                    error_words_str = "無錯誤"
                    error_word_count = 0
                    
                rows.append({
                    "族語": lang_key,
                    f"中文{phoneme_type}": ch_ph,
                    f"族語解答({phoneme_type})": gt_ph,  # 🌟 讓你能對照，不會再誤會
                    "測試次數": t,
                    "正確次數": c,
                    "錯誤次數": err_count,
                    "發生錯誤的詞數": error_word_count,
                    "正確率": f"{c/t:.2%}" if t > 0 else "0.00%",
                    "發生錯誤的詞彙": error_words_str
                })
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(by=["錯誤次數", "測試次數"], ascending=[False, False]).reset_index(drop=True)
        return df

    df_ini_detail = build_phoneme_df("聲母")
    df_fin_detail = build_phoneme_df("韻母")
    df_syll_detail = build_phoneme_df("完整音節") # 🌟 新增完整音節 Sheet

    # ==========================================
    # 寫入 Excel
    # ==========================================
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        df_summary.to_excel(writer, sheet_name="各族語整體音節正確率", index=False)
        if not df_ini_detail.empty:
            df_ini_detail.to_excel(writer, sheet_name="個別聲母正確率", index=False)
        if not df_fin_detail.empty:
            df_fin_detail.to_excel(writer, sheet_name="個別韻母正確率", index=False)
        if not df_syll_detail.empty:
            df_syll_detail.to_excel(writer, sheet_name="個別完整音節正確率", index=False)
            
    print(f"✅ 以音節為單位的正確率統計完成！報告已儲存至: {output_excel_path}")
    print(f"📊 總計測試了 {global_total_syllables} 個音節。")

if __name__ == "__main__":
    REFINED_DIR = os.path.join(current_dir, "Refined_Excel/")     
    VOTE_DIR = os.path.join(current_dir, "vote_result/")      
    OUTPUT_FILE = os.path.join(current_dir, "Phoneme_Accuracy_Results.xlsx") 
    
    DICT_FILENAME = os.path.join(MODULE_DIR, "ch_dict.json")
    CEDICT_FILENAME = os.path.join(MODULE_DIR, "cedict_normalized.json")
    
    print(f"📖 載入字典中...")
    try:
        with open(DICT_FILENAME, "r", encoding="utf-8") as f:
            ch_dict = json.load(f)
        with open(CEDICT_FILENAME, "r", encoding="utf-8") as f:
            cedict_data = json.load(f)
        cedict_index = Align_syllables03.build_cedict_index(cedict_data)
        print("✅ 字典載入完成！開始計算音節正確率...")
    except Exception as e:
        print(f"❌ 字典讀取失敗: {e}")
        exit()

    analyze_phoneme_accuracy(REFINED_DIR, VOTE_DIR, OUTPUT_FILE, ch_dict, cedict_index)