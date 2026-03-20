import json
import os

# ================= 設定區 =================
# 設定檔案範圍
START_INDEX = 1
END_INDEX = 16
current_dir = os.path.dirname(os.path.abspath(__file__))

# 設定資料夾路徑
LOCAL_DIR = os.path.abspath(os.path.join(current_dir, "../Ailgn_syllables/16族發音統計結果"))
GLOBAL_DIR = os.path.join(current_dir, "global_statistics")
OUTPUT_DIR = current_dir

# 設定摘要報告的檔名
SUMMARY_FILENAME = "low_confidence_summary.json"
# =========================================

def calculate_scores_and_merge():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 用來儲存所有低於 50% 的案例
    low_confidence_report = {}

    for i in range(START_INDEX, END_INDEX + 1):
        file_num = f"{i:02d}"
        
        local_filename = f"{file_num}_output_alignment_voted.json"
        global_filename = f"global_statistics_exclude_{file_num}.json"
        output_filename = f"{file_num}_output_alignment_voted.json"
        
        local_path = os.path.join(LOCAL_DIR, local_filename)
        global_path = os.path.join(GLOBAL_DIR, global_filename)
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        if not os.path.exists(local_path):
            print(f"⚠️ 找不到檔案: {local_path}，跳過。")
            continue
        
        if not os.path.exists(global_path):
            print(f"⚠️ 找不到 Global 檔案，分數設為 0。")
            global_data = {}
        else:
            with open(global_path, 'r', encoding='utf-8') as f:
                global_data = json.load(f)

        with open(local_path, 'r', encoding='utf-8') as f:
            local_data = json.load(f)

        final_output = {}
        file_low_confidence_list = [] # 暫存這個檔案的低信心案例

        print(f"正在處理: {file_num} ...")

        for src_char, targets in local_data.items():
            final_output[src_char] = {}
            
            total_local_count = sum(targets.values())

            # 1. 排序：由大到小
            sorted_targets = sorted(targets.items(), key=lambda x: x[1], reverse=True)

            # ==========================================
            # 🔍 [新增功能] 檢查第一名是否 <= 50%
            # ==========================================
            if total_local_count > 0 and sorted_targets:
                top_tgt, top_count = sorted_targets[0]
                top_percent = (top_count / total_local_count) * 100
                
                # 如果第一名比例 <= 50%，記錄下來
                if top_percent <= 50.0:
                    # 整理前三名候選人，方便分析混淆情況
                    candidates_info = []
                    for t, c in sorted_targets[:3]: # 只取前三名
                        p = (c / total_local_count) * 100
                        candidates_info.append(f"{t}: {p:.1f}% ({c})")
                    
                    file_low_confidence_list.append({
                        "source_char": src_char,
                        "total_count": total_local_count,
                        "top_percent": f"{top_percent:.2f}%",
                        "distribution": " | ".join(candidates_info) # 顯示分佈
                    })
            # ==========================================

            # 正常的資料處理與寫入
            for tgt_char, count in sorted_targets:
                if total_local_count > 0:
                    percent_val = (count / total_local_count) * 100
                else:
                    percent_val = 0.0
                
                percent_str = f"{percent_val:.2f}%"
                
                global_score = 0.0
                if src_char in global_data and tgt_char in global_data[src_char]:
                    g_list = global_data[src_char][tgt_char]
                    if isinstance(g_list, list) and len(g_list) >= 2 and g_list[1] > 0:
                        global_score = g_list[0] / g_list[1]
                
                final_output[src_char][tgt_char] = {
                    "local_count": count,
                    "global_score_i": round(global_score, 4),
                    "percent": percent_str
                }

        # 如果這個檔案有低信心的案例，加入總報告
        if file_low_confidence_list:
            # 依照「總次數」排序，讓樣本數多的問題排前面
            file_low_confidence_list.sort(key=lambda x: x["total_count"], reverse=True)
            low_confidence_report[f"File_{file_num}"] = file_low_confidence_list

        # 寫入原本的結果檔案
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
            
        print(f"✅ 已建立: {output_filename}")

    # ==========================================
    # 📝 輸出低信心度總結報告
    # ==========================================
    summary_path = os.path.join(OUTPUT_DIR, SUMMARY_FILENAME)
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(low_confidence_report, f, ensure_ascii=False, indent=4)
    
    print("-" * 30)
    print(f"📊 統計完成！低於 50% 的案例已整理至: {SUMMARY_FILENAME}")
    print(f"   共發現 {len(low_confidence_report)} 個檔案含有低信心案例。")

if __name__ == "__main__":
    calculate_scores_and_merge()
