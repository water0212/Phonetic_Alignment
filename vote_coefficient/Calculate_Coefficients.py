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

def calculate_i_score(src, tgt, global_data, global_denominators):
    """
    輔助函式：計算全域分數 i
    i = (強勢度/總強勢度 * 0.7) + (出現次數/總出現次數 * 0.3)
    """
    if src not in global_data or tgt not in global_data[src]:
        return 0.0
    
    g_stats = global_data[src][tgt] # [rank, count]
    g_rank = g_stats[0]
    g_count = g_stats[1]
    
    # 取得分母
    denoms = global_denominators.get(src, {'sum_rank': 0, 'sum_count': 0})
    sum_rank = denoms['sum_rank']
    sum_count = denoms['sum_count']

    part_rank = (g_rank / sum_rank) if sum_rank > 0 else 0
    part_count = (g_count / sum_count) if sum_count > 0 else 0
    
    return (part_rank * 0.7) + (part_count * 0.3)

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
    global_denominators = {}
    for src, targets in global_data.items():
        sum_rank = 0
        sum_count = 0
        if isinstance(targets, dict): 
            for tgt, stats in targets.items():
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

        # 針對該檔案的每一個 Source (例如 "b", "o")
        for src, targets in local_data.items():
            temp_results = []

            # =================================================
            # 情況 A: 本地有資料 (例如 "b": {"p": 10})
            # =================================================
            if targets:
                local_total_count = sum(targets.values())

                for tgt, count in targets.items():
                    # 計算 k (個別分數)
                    k_score = count / local_total_count if local_total_count > 0 else 0

                    # 計算 i (全域分數)
                    i_score = calculate_i_score(src, tgt, global_data, global_denominators)

                    # 計算總分
                    total_score = k_score + i_score

                    temp_results.append({
                        'target': tgt,
                        'data': {
                            'local_score_k': round(k_score, 4),
                            'global_score_i': round(i_score, 4),
                            'total_score': round(total_score, 4)
                        }
                    })

            # =================================================
            # 情況 B: 本地無資料 (例如 "o": {}) -> 啟動自動填補
            # =================================================
            else:
                # 檢查 Global 是否有這個 Source 的資料
                if src in global_data and global_data[src]:
                    # 尋找 Global 中分數最高的 Target
                    best_target = None
                    max_i_score = -1.0

                    # 遍歷 Global 中該 Source 的所有 Target
                    for g_tgt in global_data[src]:
                        current_i = calculate_i_score(src, g_tgt, global_data, global_denominators)
                        
                        if current_i > max_i_score:
                            max_i_score = current_i
                            best_target = g_tgt
                    
                    # 如果找到了最佳替補
                    if best_target is not None:
                        temp_results.append({
                            'target': best_target,
                            'data': {
                                'local_score_k': 0.0,          # 本地沒出現，所以 k=0
                                'global_score_i': round(max_i_score, 4),
                                'total_score': round(max_i_score, 4), # 總分 = i
                                'note': 'Auto-filled from Global' # (選用) 標記這是自動填補的
                            }
                        })

            # --- 排序 (由大到小) ---
            temp_results.sort(key=lambda x: x['data']['total_score'], reverse=True)

            # --- 重組回字典格式 ---
            processed_data[src] = {}
            for item in temp_results:
                processed_data[src][item['target']] = item['data']

        # 5. 輸出結果
        output_path = os.path.join(current_dir, filename) 
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=4)
            
        print(f"   ✅ 已輸出: {filename}")

    print("🎉 所有檔案處理完成！")

if __name__ == "__main__":
    main()
