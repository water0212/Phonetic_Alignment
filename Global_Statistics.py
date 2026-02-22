import json
import os

# --- 設定 ---
FOLDER_NAME = '16族發音統計結果'
FILE_COUNT = 16
OUTPUT_FILENAME = 'global_statistics.json'

def main():
    # 取得目前腳本的路徑
    base_path = os.path.dirname(os.path.abspath(__file__))
    vote_dir = os.path.join(base_path, FOLDER_NAME)
    output_path = os.path.join(base_path,"vote_coefficient", OUTPUT_FILENAME)

    # 用來儲存全域統計結果
    # 結構: global_stats[source][target] = [Top_Rank_Score, Total_Count]
    global_stats = {}

    print(f"📂 開始讀取 {FOLDER_NAME} 資料夾下的 {FILE_COUNT} 個檔案...")

    # 1. 遍歷 16 個檔案
    for i in range(1, FILE_COUNT + 1):
        filename = f"{i:02d}_output_alignment_voted.json"
        file_path = os.path.join(vote_dir, filename)

        if not os.path.exists(file_path):
            print(f"⚠️ 警告: 找不到檔案 {filename}，跳過。")
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
        except json.JSONDecodeError:
            print(f"❌ 錯誤: 無法讀取 {filename} (格式錯誤)")
            continue

        # 2. 分析單個檔案
        for src, target_map in file_data.items():
            
            if src not in global_stats:
                global_stats[src] = {}
                
            if not target_map:
                continue

            # 找出該檔案中，該 source 對應次數最高的數值 (Local Max)
            # 例如: "j": {"c": 18, "z": 2} -> local_max = 18
            local_max = max(target_map.values())

            for tgt, count in target_map.items():
                # 確保 target 在全域字典中存在，預設值為 [0, 0]
                if tgt not in global_stats[src]:
                    global_stats[src][tgt] = [0, 0] 

                # --- 更新數值 2: 總次數 (Total Count) ---
                global_stats[src][tgt][1] += count

                # --- 更新數值 1: 是否為該檔案的最常出現 (Top Rank) ---
                # 如果目前的 count 等於該檔案的最大值，則 Top Rank + 1
                # (注意：如果有兩個 target 次數一樣多且都是最大，兩個都會 +1)
                if count == local_max:
                    global_stats[src][tgt][0] += 1

    # 3. 輸出 JSON 檔案
    print(f"💾 正在儲存結果至 {OUTPUT_FILENAME} ...")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # indent=4 讓輸出的 JSON 縮排漂亮，方便閱讀
        json.dump(global_stats, f, ensure_ascii=False, indent=4)

    print("✅ 完成！")

if __name__ == "__main__":
    main()
