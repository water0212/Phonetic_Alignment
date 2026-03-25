import pandas as pd
import re
import os
from openpyxl.styles import PatternFill

def parse_phoneme(pred_str):
    """從預測字串中提取 Top 1 的發音"""
    if not pred_str or pred_str == "N/A":
        return "N/A"
    return pred_str.split('(')[0].strip()

def get_vote_comparison(pred_str):
    """
    解析預測字串，判斷第一名與第二名 LOO 票數的大小關係
    """
    if not pred_str or pred_str == "N/A":
        return "N/A"
    
    matches = re.findall(r'=(\d+),\s*D:', pred_str)
    
    if len(matches) >= 2:
        top1_votes = int(matches[0])
        top2_votes = int(matches[1])
        
        if top1_votes > top2_votes:
            return "大於 (Top1 > Top2)"
        elif top1_votes == top2_votes:
            return "等於 (票數平手)"
        else:
            return "小於 (Top1 < Top2)" 
            
    elif len(matches) == 1:
        return "無第二名"
    else:
        return "解析失敗"

def analyze_errors(input_excel_path, output_excel_path):
    print(f"📥 正在讀取測試結果: {input_excel_path}")
    
    if not os.path.exists(input_excel_path):
        print("❌ 找不到輸入檔案，請確認路徑是否正確！")
        return

    try:
        df = pd.read_excel(input_excel_path, sheet_name="詳細結果")
    except Exception as e:
        print(f"❌ 讀取 Excel 失敗: {e}")
        return
        
    error_df = df[df["是否完全正確"] == "否"].copy()
    print(f"🔍 總共發現 {len(error_df)} 筆預測錯誤的詞彙，開始進行解析...")

    # 🌟 新增欄位，用來精準記錄是哪個部分發生平手錯誤
    error_df["平手錯誤類型"] = "無"

    initial_errors_dict = {}
    final_errors_dict = {}

    pattern = re.compile(r"中\((.*?),(.*?)\) -> 預測:\[(.*?)\] \| \[(.*?)\] \| 解答\((.*?),(.*?)\)")

    for idx, row in error_df.iterrows():
        lang = row["族語"]
        word = str(row["中文詞彙"])
        details = str(row["測試過程與比對"]).split('\n')
        
        has_ini_tie = False
        has_fin_tie = False
        
        for line in details:
            if line.startswith("▶"):
                continue
                
            match = pattern.search(line)
            if match:
                ch_ini, ch_fin, pred_ini_str, pred_fin_str, gt_ini, gt_fin = match.groups()
                
                pred_ini = parse_phoneme(pred_ini_str)
                pred_fin = parse_phoneme(pred_fin_str)
                
                ini_vote_diff = get_vote_comparison(pred_ini_str)
                fin_vote_diff = get_vote_comparison(pred_fin_str)
                
                # --- 記錄聲母錯誤 ---
                if pred_ini != gt_ini:
                    if ini_vote_diff == "等於 (票數平手)":
                        has_ini_tie = True
                        
                    ini_key = (lang, ch_ini, gt_ini, pred_ini, ini_vote_diff)
                    if ini_key not in initial_errors_dict:
                        initial_errors_dict[ini_key] = {"count": 0, "words": set()}
                    initial_errors_dict[ini_key]["count"] += 1
                    initial_errors_dict[ini_key]["words"].add(word)
                    
                # --- 記錄韻母錯誤 ---
                if pred_fin != gt_fin:
                    if fin_vote_diff == "等於 (票數平手)":
                        has_fin_tie = True
                        
                    fin_key = (lang, ch_fin, gt_fin, pred_fin, fin_vote_diff)
                    if fin_key not in final_errors_dict:
                        final_errors_dict[fin_key] = {"count": 0, "words": set()}
                    final_errors_dict[fin_key]["count"] += 1
                    final_errors_dict[fin_key]["words"].add(word)
        
        # 🌟 根據平手錯誤發生的部位，寫入對應的類型
        if has_ini_tie and has_fin_tie:
            error_df.at[idx, "平手錯誤類型"] = "聲母與韻母"
        elif has_ini_tie:
            error_df.at[idx, "平手錯誤類型"] = "聲母"
        elif has_fin_tie:
            error_df.at[idx, "平手錯誤類型"] = "韻母"

    # ==========================================
    # 轉換統計結果為 DataFrame
    # ==========================================
    ini_stats = []
    for key, data in initial_errors_dict.items():
        lang, ch_ini, gt_ini, pred_ini, vote_diff = key
        ini_stats.append({
            "族語": lang,
            "中文聲母": ch_ini,
            "官方解答": gt_ini,
            "模型預測": pred_ini,
            "Top1與Top2票數狀態": vote_diff,
            "錯誤發生次數": data["count"],
            "發生錯誤的詞彙": ", ".join(sorted(list(data["words"])))
        })
        
    fin_stats = []
    for key, data in final_errors_dict.items():
        lang, ch_fin, gt_fin, pred_fin, vote_diff = key
        fin_stats.append({
            "族語": lang,
            "中文韻母": ch_fin,
            "官方解答": gt_fin,
            "模型預測": pred_fin,
            "Top1與Top2票數狀態": vote_diff,
            "錯誤發生次數": data["count"],
            "發生錯誤的詞彙": ", ".join(sorted(list(data["words"])))
        })

    df_ini_stats = pd.DataFrame(ini_stats)
    if not df_ini_stats.empty:
        df_ini_stats = df_ini_stats.sort_values(by=["錯誤發生次數", "Top1與Top2票數狀態"], ascending=[False, True]).reset_index(drop=True)

    df_fin_stats = pd.DataFrame(fin_stats)
    if not df_fin_stats.empty:
        df_fin_stats = df_fin_stats.sort_values(by=["錯誤發生次數", "Top1與Top2票數狀態"], ascending=[False, True]).reset_index(drop=True)

    # ==========================================
    # 匯出分析報告至 Excel 並進行儲存格上色
    # ==========================================
    print(f"💾 正在產生包含「多色平手標示」的分析報告...")
    with pd.ExcelWriter(output_excel_path, engine='openpyxl') as writer:
        if not df_ini_stats.empty:
            df_ini_stats.to_excel(writer, sheet_name="聲母錯誤統計", index=False)
        else:
            pd.DataFrame({"訊息": ["沒有發現聲母錯誤"]}).to_excel(writer, sheet_name="聲母錯誤統計", index=False)
            
        if not df_fin_stats.empty:
            df_fin_stats.to_excel(writer, sheet_name="韻母錯誤統計", index=False)
        else:
            pd.DataFrame({"訊息": ["沒有發現韻母錯誤"]}).to_excel(writer, sheet_name="韻母錯誤統計", index=False)
            
        error_df.to_excel(writer, sheet_name="錯誤詞彙總覽", index=False)
        
        # 🌟 準備三種不同的顏色樣式
        ws = writer.sheets["錯誤詞彙總覽"]
        
        fill_ini = PatternFill(start_color="FFCC99", end_color="FFCC99", fill_type="solid")   # 淺橘 (聲母)
        fill_fin = PatternFill(start_color="CCFFCC", end_color="CCFFCC", fill_type="solid")   # 淺綠 (韻母)
        fill_both = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")  # 淺黃 (都有)
        
        for row_idx, tie_type in enumerate(error_df["平手錯誤類型"], start=2):
            target_fill = None
            
            if tie_type == "聲母":
                target_fill = fill_ini
            elif tie_type == "韻母":
                target_fill = fill_fin
            elif tie_type == "聲母與韻母":
                target_fill = fill_both
                
            # 若有配對到顏色，則將該列整行塗色
            if target_fill:
                for col_idx in range(1, len(error_df.columns) + 1):
                    ws.cell(row=row_idx, column=col_idx).fill = target_fill
        
    print(f"✅ 錯誤分析完成！報告已儲存至: {output_excel_path}")
    print(f"🎨 顏色標示說明: 淺橘色(聲母)、淺綠色(韻母)、淺黃色(兩者皆是)")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    INPUT_FILE = os.path.join(current_dir, "LOOCV_Results.xlsx") 
    OUTPUT_FILE = os.path.join(current_dir, "Error_Analysis_Report.xlsx") 

    analyze_errors(INPUT_FILE, OUTPUT_FILE)