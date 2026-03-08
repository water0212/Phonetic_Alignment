import json
import os
import glob
import pandas as pd

def process_loo_validation(refined_dir, loo_dir, output_excel_path):
    # 找尋資料夾內所有的 refined_ JSON 檔案
    refined_pattern = os.path.join(refined_dir, "refined_*.json")
    refined_files = glob.glob(refined_pattern)
    
    if not refined_files:
        print(f"⚠️ 警告：在 {refined_dir} 找不到任何 refined_*.json 檔案，請檢查路徑是否正確。")
        return

    all_results = []
    
    # 統計變數
    global_total = 0
    global_correct = 0
    ini_correct_total = 0
    fin_correct_total = 0
    language_stats = {}  # 用來記錄各族的統計資料
    
    for refined_file in refined_files:
        base_name = os.path.basename(refined_file)
        parts = base_name.split('_')
        prefix_num = parts[1] if len(parts) > 1 else "Unknown"
        lang_name = parts[2] if len(parts) > 2 else f"Language_{prefix_num}"
        
        lang_key = f"{prefix_num}_{lang_name}"
        
        if lang_key not in language_stats:
            language_stats[lang_key] = {
                "total": 0,
                "correct": 0,
                "ini_correct": 0,
                "fin_correct": 0,
            }
            
        loo_file = os.path.join(loo_dir, f"{prefix_num}_LOO_analysis.json")
        
        if not os.path.exists(loo_file):
            print(f"⚠️ 找不到對應的 LOO 檔案: {loo_file}，略過 {base_name}")
            continue
            
        with open(refined_file, 'r', encoding='utf-8') as f:
            refined_data = json.load(f)
            
        with open(loo_file, 'r', encoding='utf-8') as f:
            loo_analysis = json.load(f)
            
        for entry in refined_data:
            word = entry.get("chinese", "")
            alignment = entry.get("alignment", [])
            
            word_is_correct = True
            ini_correct = True
            fin_correct = True
            process_details = []
            
            for align in alignment:
                # 取得中文拼音拆解
                ch_syl = align.get("chinese_syllable", {})
                ch_ini = ch_syl.get("initial", "") or "0c"
                ch_fin = ch_syl.get("final", "") or "0v"
                
                # 取得標準答案的族語拼音
                ts_syl = align.get("tsou_syllable", {})
                gt_ini = ts_syl.get("initial", "") or "0c"
                gt_fin = ts_syl.get("final", "") or "0v"
                
                # ===== 預測聲母 =====
                pred_ini = None
                if ch_ini in loo_analysis:
                    remove_key = f"remove_{gt_ini}"
                    loo_res = loo_analysis[ch_ini].get("loo_test_results", {})
                    if remove_key in loo_res:
                        pred_ini = loo_res[remove_key].get("new_winner")
                    else:
                        pred_ini = loo_analysis[ch_ini].get("original_winner")
                
                # ===== 預測韻母 =====
                pred_fin = None
                if ch_fin in loo_analysis:
                    remove_key = f"remove_{gt_fin}"
                    loo_res = loo_analysis[ch_fin].get("loo_test_results", {})
                    if remove_key in loo_res:
                        pred_fin = loo_res[remove_key].get("new_winner")
                    else:
                        pred_fin = loo_analysis[ch_fin].get("original_winner")
                
                # 比對
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
            if ini_correct:
                ini_correct_total += 1
                language_stats[lang_key]["ini_correct"] += 1
            if fin_correct:
                fin_correct_total += 1
                language_stats[lang_key]["fin_correct"] += 1
                
            all_results.append({
                "族語": lang_key,
                "中文詞彙": word,
                "測試過程與比對": "\n".join(process_details),
                "是否完全正確": "是" if word_is_correct else "否"
            })

    # ==========================
    # 產生統計結果
    # ==========================
    if global_total == 0:
        print("❌ 沒有成功處理任何資料，請檢查資料夾路徑與檔案名稱格式是否正確。")
        return

    stats_rows = []
    for lang_key, stats in language_stats.items():
        t = stats["total"]
        c = stats["correct"]
        i = stats["ini_correct"]
        f = stats["fin_correct"]
        acc = c / t if t > 0 else 0
        stats_rows.append({
            "族語名稱": lang_key,
            "總測試詞數": t,
            "聲母正確數": i,
            "聲母正確率": f"{i / t:.2%}" if t > 0 else "0.00%",
            "韻母正確數": f,
            "韻母正確率": f"{f / t:.2%}" if t > 0 else "0.00%",
            "完全正確詞數": c,
            "完全正確率": f"{acc:.2%}",
        })
        
    global_acc = global_correct / global_total if global_total > 0 else 0
    stats_rows.append({
        "族語名稱": "【整體總計】",
        "總測試詞數": global_total,
        "聲母正確數": ini_correct_total,
        "聲母正確率": f"{ini_correct_total / global_total:.2%}" if global_total > 0 else "0.00%",
        "韻母正確數": fin_correct_total,
        "韻母正確率": f"{fin_correct_total / global_total:.2%}" if global_total > 0 else "0.00%",
        "完全正確詞數": global_correct,
        "完全正確率": f"{global_acc:.2%}",
    })
    
    df_stats = pd.DataFrame(stats_rows)
    df_details = pd.DataFrame(all_results)
    
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        df_stats.to_excel(writer, sheet_name="正確率統計", index=False)
        df_details.to_excel(writer, sheet_name="詳細結果", index=False)
        
    print(f"✅ 已成功匯出 LOO 測試結果至: {output_excel_path}")
    print(f"✅ 整體總正確率為: {global_acc:.2%}")

if __name__ == "__main__":
    # --------------------------------------------------------------------
    # 在這裡設定您的「相對路徑」
    # ../ 代表上一層資料夾。請根據您執行 Python 腳本的「當前位置」進行修改
    # --------------------------------------------------------------------
    REFINED_DIR = "Refined_Excel/"      # 存放 refined_XX_XX語.json 的資料夾
    LOO_DIR = "vote_result/16族最終權重結果_LOO測試/"             # 存放 XX_LOO_analysis.json 的資料夾
    OUTPUT_FILE = "./LOO_Validation_Results.xlsx" # 輸出的 Excel 檔案位置
    
    print(f"準備讀取 Refined 資料夾: {REFINED_DIR}")
    print(f"準備讀取 LOO 資料夾: {LOO_DIR}")
    
    process_loo_validation(REFINED_DIR, LOO_DIR, OUTPUT_FILE)