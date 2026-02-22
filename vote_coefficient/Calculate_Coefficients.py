import json
import os

# --- 設定 ---
# 資料來源資料夾 (相對於本程式的位置)
# 假設結構為:
# /專案目錄
#    /vote              <-- 讀取這裡的原始檔案
#    /vote_coefficient  <-- 本程式與 global_statistics.json 在這裡
VOTE_FOLDER_NAME = '16族發音統計結果'
GLOBAL_STATS_FILENAME = 'global_statistics.json'

def main():
    # 1. 設定路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 往上一層找 vote 資料夾
    vote_dir = os.path.join(os.path.dirname(current_dir), VOTE_FOLDER_NAME)
    
    # global_statistics.json 就在本程式旁邊
    global_stats_path = os.path.join(current_dir, GLOBAL_STATS_FILENAME)

    # 檢查必要檔案
    if not os.path.exists(global_stats_path):
        print(f"❌ 錯誤: 找不到全域統計檔 {global_stats_path}")
        return
    if not os.path.exists(vote_dir):
        print(f"❌ 錯誤: 找不到 vote 資料夾 {vote_dir}")
        return

    # 2. 讀取 Global Statistics
    print(f"📖 讀取全域統計: {GLOBAL_STATS_FILENAME} ...")
    with open(global_stats_path, 'r', encoding='utf-8') as f:
        global_data = json.load(f)

    # 3. 預先計算 Global 的分母 (為了計算 i 分數)
    # global_denominators[src] = {'total_rank': sum, 'total_count': sum}
    global_denominators = {}
    for src, targets in global_data.items():
        sum_rank = 0
        sum_count = 0
        if isinstance(targets, dict): # 確保不是空的
            for tgt, stats in targets.items():
                # stats[0] 是 Top Rank, stats[1] 是 Total Count
                sum_rank += stats[0]
                sum_count += stats[1]
        
        global_denominators[src] = {
            'sum_rank': sum_rank,
            'sum_count': sum_count
        }

    # 4. 遍歷 vote 資料夾中的所有 JSON
    vote_files = [f for f in os.listdir(vote_dir) if f.endswith('.json')]
    print(f"📂 找到 {len(vote_files)} 個檔案，開始計算分數...")

    for filename in vote_files:
        file_path = os.path.join(vote_dir, filename)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            local_data = json.load(f)
        
        processed_data = {}

        # 針對該檔案的每一個 Source (例如 "b")
        for src, targets in local_data.items():
            if not targets:
                processed_data[src] = {}
                continue

            # 計算 Local 分母 (該檔案中，這個 Source 出現的總次數)
            # k 的分母
            local_total_count = sum(targets.values())

            # 暫存該 Source 的所有 Target 結果，以便稍後排序
            temp_results = []

            for tgt, count in targets.items():
                # --- 計算 k (個別分數) ---
                # k = 該元素次數 / 該 Source 總次數
                k_score = count / local_total_count if local_total_count > 0 else 0

                # --- 計算 i (全域分數) ---
                i_score = 0
                
                # 從 global 資料撈取數據
                if src in global_data and tgt in global_data[src]:
                    g_stats = global_data[src][tgt] # [rank, count]
                    g_rank = g_stats[0]
                    g_count = g_stats[1]
                    
                    # 取得分母
                    denoms = global_denominators.get(src, {'sum_rank': 0, 'sum_count': 0})
                    sum_rank = denoms['sum_rank']
                    sum_count = denoms['sum_count']

                    # i = (強勢度/總強勢度 * 0.7) + (出現次數/總出現次數 * 0.3)
                    part_rank = (g_rank / sum_rank) if sum_rank > 0 else 0
                    part_count = (g_count / sum_count) if sum_count > 0 else 0
                    
                    i_score = (part_rank * 0.7) + (part_count * 0.3)

                # --- 計算總分 ---
                total_score = k_score + i_score

                # 存入暫存列表
                temp_results.append({
                    'target': tgt,
                    'data': {
                        'local_score_k': round(k_score, 4),
                        'global_score_i': round(i_score, 4),
                        'total_score': round(total_score, 4)
                    }
                })

            # --- 排序 ---
            # 根據 total_score 由大到小排序
            temp_results.sort(key=lambda x: x['data']['total_score'], reverse=True)

            # --- 重組回字典格式 ---
            processed_data[src] = {}
            for item in temp_results:
                processed_data[src][item['target']] = item['data']

        # 5. 輸出結果到 vote_coefficient 資料夾
        output_path = os.path.join(current_dir, filename) # 檔名保持一致
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=4)
            
        print(f"   ✅ 已輸出: {filename}")

    print("🎉 所有檔案處理完成！")

if __name__ == "__main__":
    main()
