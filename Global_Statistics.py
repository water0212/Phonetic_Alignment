import json
import os

# --- 設定 ---
FOLDER_NAME = '16族發音統計結果'
FILE_COUNT = 16
OUTPUT_DIR_NAME = "vote_result/global_statistics"

def main():
    base_path = os.path.dirname(os.path.abspath(__file__))
    vote_dir = os.path.join(base_path, FOLDER_NAME)
    output_dir = os.path.join(base_path, OUTPUT_DIR_NAME)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"📂 正在預載入 {FILE_COUNT} 個檔案的資料...")
    all_files_data = {}

    for i in range(1, FILE_COUNT + 1):
        filename = f"{i:02d}_output_alignment_voted.json"
        file_path = os.path.join(vote_dir, filename)

        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    all_files_data[i] = json.load(f)
            except json.JSONDecodeError:
                print(f"❌ 錯誤: 無法讀取 {filename}")
        else:
            all_files_data[i] = {}

    print(f"✅ 資料載入完成，開始執行 Global Statistics 計算...\n")

    for exclude_id in range(1, FILE_COUNT + 1):
        
        # 暫存變數
        # temp_counts: 記錄分子 {src: {tgt: count}}
        temp_counts = {}
        # temp_totals: 記錄分母 {src: total_count}
        temp_totals = {}
        
        for fid, file_data in all_files_data.items():
            if fid == exclude_id:
                continue

            for src, target_map in file_data.items():
                # 1. 計算該檔案中，這個聲母 src 的總次數
                file_src_total = sum(target_map.values())
                
                # 累加到全域分母 (只要有出現 src，不管對應到誰，都要加)
                if src not in temp_totals:
                    temp_totals[src] = 0
                temp_totals[src] += file_src_total

                # 2. 累加分子
                if src not in temp_counts:
                    temp_counts[src] = {}
                
                for tgt, count in target_map.items():
                    if tgt not in temp_counts[src]:
                        temp_counts[src][tgt] = 0
                    temp_counts[src][tgt] += count

        # --- 組裝最終結果 ---
        final_global_stats = {}
        
        for src, targets in temp_counts.items():
            final_global_stats[src] = {}
            # 取得該聲母的正確全域總數 (分母)
            global_total = temp_totals.get(src, 0)
            
            for tgt, count in targets.items():
                # 格式: [分子(該對應次數), 分母(該聲母總次數)]
                final_global_stats[src][tgt] = [count, global_total]

        output_filename = f"global_statistics_exclude_{exclude_id:02d}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_global_stats, f, ensure_ascii=False, indent=4)

        print(f"   💾 已儲存: {output_filename} (排除第 {exclude_id:02d} 族)")

    print("\n🎉 全部完成！分母計算邏輯已修正。")

if __name__ == "__main__":
    main()
