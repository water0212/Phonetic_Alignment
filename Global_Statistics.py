import json
import os

# --- 設定 ---
FOLDER_NAME = '16族發音統計結果'
FILE_COUNT = 16
OUTPUT_DIR_NAME = "vote_result/global_statistics"

def main():
    # 取得目前腳本的路徑
    base_path = os.path.dirname(os.path.abspath(__file__))
    vote_dir = os.path.join(base_path, FOLDER_NAME)
    output_dir = os.path.join(base_path, OUTPUT_DIR_NAME)

    # 確保輸出資料夾存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. 先讀取所有檔案到記憶體 (避免重複 I/O)
    print(f"📂 正在預載入 {FILE_COUNT} 個檔案的資料...")
    all_files_data = {} # 格式: {file_id: json_data}

    for i in range(1, FILE_COUNT + 1):
        filename = f"{i:02d}_output_alignment_voted.json"
        file_path = os.path.join(vote_dir, filename)

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    all_files_data[i] = json.load(f)
            except json.JSONDecodeError:
                print(f"❌ 錯誤: 無法讀取 {filename} (格式錯誤)")
        else:
            print(f"⚠️ 警告: 找不到檔案 {filename}，將視為空資料。")
            all_files_data[i] = {}

    print(f"✅ 資料載入完成，開始執行 'Leave-One-Out' 統計生成...\n")

    # 2. 執行 16 次迴圈，每次排除一個 ID
    for exclude_id in range(1, FILE_COUNT + 1):
        
        # 用來儲存本次 (排除 exclude_id 後) 的全域統計結果
        # 結構: global_stats[source][target] = [Top_Rank_Score, Total_Count]
        current_global_stats = {}
        
        # 遍歷所有已載入的資料
        for fid, file_data in all_files_data.items():
            # 【關鍵修改】如果目前的檔案 ID 等於要排除的 ID，則跳過不計
            if fid == exclude_id:
                continue

            # 開始分析單個檔案 (邏輯與之前相同)
            for src, target_map in file_data.items():
                if src not in current_global_stats:
                    current_global_stats[src] = {}
                    
                if not target_map:
                    continue

                # 找出該檔案中，該 source 對應次數最高的數值 (Local Max)
                local_max = max(target_map.values())

                for tgt, count in target_map.items():
                    if tgt not in current_global_stats[src]:
                        current_global_stats[src][tgt] = [0, 0] 

                    # 更新數值 2: 總次數
                    current_global_stats[src][tgt][1] += count

                    # 更新數值 1: Top Rank
                    if count == local_max:
                        current_global_stats[src][tgt][0] += 1

        # 3. 輸出該次排除後的 JSON 檔案
        # 檔名範例: global_statistics_exclude_01.json (給第 1 族用的，裡面不含第 1 族資料)
        output_filename = f"global_statistics_exclude_{exclude_id:02d}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(current_global_stats, f, ensure_ascii=False, indent=4)

        print(f"   💾 已儲存: {output_filename} (排除第 {exclude_id:02d} 族)")

    print("\n🎉 全部完成！已生成 16 個對應的 Global 統計檔。")

if __name__ == "__main__":
    main()
