import json
import os

# ================= 設定區 =================
# 設定檔案範圍
START_INDEX = 1
END_INDEX = 19
current_dir = os.path.dirname(os.path.abspath(__file__))
# 設定資料夾路徑 (如果檔案都在同一層，保持預設即可)
LOCAL_DIR = os.path.join(current_dir, "../16族發音統計結果")  # 存放 01_output_alignment_voted.json 的位置
GLOBAL_DIR = os.path.join(current_dir, "global_statistics")  # 存放 global_statistics_exclude_01.json 的資料夾
OUTPUT_DIR = current_dir  # 輸出檔案的位置
# =========================================

def calculate_scores_and_merge():
    # 確保輸出目錄存在
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    for i in range(START_INDEX, END_INDEX + 1):
        file_num = f"{i:02d}"
        
        # 定義檔名
        local_filename = f"{file_num}_output_alignment_voted.json"
        global_filename = f"global_statistics_exclude_{file_num}.json"
        output_filename = f"{file_num}_output_alignment_voted.json"
        
        local_path = os.path.join(LOCAL_DIR, local_filename)
        global_path = os.path.join(GLOBAL_DIR, global_filename)
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        # 檢查檔案是否存在
        if not os.path.exists(local_path):
            print(f"⚠️ 找不到檔案: {local_path}，跳過。")
            continue
        
        if not os.path.exists(global_path):
            print(f"⚠️ 找不到 Global 檔案: {global_path}，Global 分數將設為 0。")
            global_data = {}
        else:
            with open(global_path, 'r', encoding='utf-8') as f:
                global_data = json.load(f)

        # 讀取 Local 檔案
        with open(local_path, 'r', encoding='utf-8') as f:
            local_data = json.load(f)

        final_output = {}

        print(f"正在處理: {file_num} ...")

        # 遍歷每一個聲母 (例如 "b", "d")
        for src_char, targets in local_data.items():
            final_output[src_char] = {}
            
            # 計算 Local 的總數 (分母)
            # targets 結構範例: {"p": 12, "b": 1} -> total = 13
            total_local_count = sum(targets.values())

            # 遍歷每一個預測結果 (例如 "p", "t")
            for tgt_char, count in targets.items():
                # 1. 計算 Local Score (該對應次數 / 該聲母總次數)
                local_score = count / total_local_count if total_local_count > 0 else 0.0
                
                # 2. 取得 Global Score
                # Global 結構範例: "b": { "p": [12, 81] } -> [次數, 總數]
                global_score = 0.0
                if src_char in global_data and tgt_char in global_data[src_char]:
                    g_list = global_data[src_char][tgt_char]
                    # 確保格式是 list 且長度足夠，且分母不為 0
                    if isinstance(g_list, list) and len(g_list) >= 2 and g_list[1] > 0:
                        global_score = g_list[0] / g_list[1]
                
                # 3. 組合資料
                final_output[src_char][tgt_char] = {
                    "local_count": count,
                    "local_score_k": round(local_score, 4),   # 取小數點後4位
                    "global_score_i": round(global_score, 4), # 取小數點後4位
                    "note": "Local Vote"
                }

        # 寫入結果檔案
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
            
        print(f"✅ 已建立: {output_filename}")

if __name__ == "__main__":
    calculate_scores_and_merge()
