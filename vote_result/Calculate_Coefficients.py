import json
import os
import copy

# === 設定區 ===
VOTE_FOLDER_NAME = '16族發音統計結果'
GLOBAL_STATS_PREFIX = 'global_statistics_exclude_' 
DICT_FOLDER_NAME = 'fm_dict' 
OUTPUT_FOLDER_NAME = '16族最終權重結果_LOO測試' # 新的輸出位置

# 權重設定 (用於計算 Global Score)
RANK_WEIGHT = 0.7
COUNT_WEIGHT = 0.3

def calculate_i_score(src, tgt, global_data, global_denominators):
    """
    計算全域分數 i (保持不變)
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
    
    return (part_rank * RANK_WEIGHT) + (part_count * COUNT_WEIGHT)

def calculate_candidates_scores(src, current_targets, global_data, global_denominators):
    """
    核心計算邏輯：傳入一組 targets (可能是原始的，也可能是減 1 後的)，
    回傳計算好分數的候選人列表。
    """
    candidates = {}
    local_total_count = sum(current_targets.values())

    for tgt, count in current_targets.items():
        # 1. 計算 Local Score (k)
        k_score = count / local_total_count if local_total_count > 0 else 0
        
        # 2. 計算 Global Score (i)
        i_score = calculate_i_score(src, tgt, global_data, global_denominators)
        
        # 3. 存入資料
        candidates[tgt] = {
            'local_count': count,
            'local_score_k': round(k_score, 4),
            'global_score_i': round(i_score, 4),
            # 這裡可以定義一個綜合分數，目前邏輯主要是看 local_count，輔以 global_i
            # 為了方便排序，我們之後會用到 tuple
        }
    return candidates

def get_winner(candidates_dict):
    """
    決定贏家是誰
    規則：
    1. Local Count 越高越好
    2. 如果 Local Count 一樣，Global Score 越高越好
    """
    if not candidates_dict:
        return None, 0
        
    # 轉成 list 進行排序: (target, data)
    items = list(candidates_dict.items())
    
    # 排序鍵：(local_count, global_score_i) 都是由大到小
    # Python 的 sort 是穩定的，且 tuple 比較是依序比較
    items.sort(key=lambda x: (x[1]['local_count'], x[1]['global_score_i']), reverse=True)
    
    winner_target = items[0][0]
    winner_data = items[0][1]
    
    # 這裡回傳贏家名稱，以及一個代表分數的數值(這裡暫用 local_score_k 代表信心度)
    return winner_target, winner_data['local_score_k']

def main():
    # 1. 設定路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    vote_dir = os.path.join(os.path.dirname(current_dir), VOTE_FOLDER_NAME)
    output_dir = os.path.join(current_dir, OUTPUT_FOLDER_NAME)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not os.path.exists(vote_dir):
        print(f"❌ 錯誤: 找不到 vote 資料夾 {vote_dir}")
        return

    # 2. 遍歷 vote 資料夾中的所有 JSON
    vote_files = [f for f in os.listdir(vote_dir) if f.endswith('.json')]
    print(f"📂 找到 {len(vote_files)} 個檔案，開始執行 LOO 敏感度分析...")

    for filename in vote_files:
        file_path = os.path.join(vote_dir, filename)
        file_id = filename.split('_')[0] 
        
        # --- 讀取 Global Statistics ---
        global_filename = f"{GLOBAL_STATS_PREFIX}{file_id}.json"
        global_stats_path = os.path.join(current_dir, "global_statistics", global_filename)
        
        if not os.path.exists(global_stats_path):
            global_stats_path = os.path.join(current_dir, global_filename)

        if not os.path.exists(global_stats_path):
            print(f"⚠️ 跳過 {filename}: 找不到 Global 檔")
            continue

        with open(global_stats_path, 'r', encoding='utf-8') as f:
            global_data = json.load(f)

        # --- 計算 Global 分母 ---
        global_denominators = {}
        for src, targets in global_data.items():
            sum_rank = 0
            sum_count = 0
            if isinstance(targets, dict): 
                for tgt, stats in targets.items():
                    sum_rank += stats[0]
                    sum_count += stats[1]
            global_denominators[src] = {'sum_rank': sum_rank, 'sum_count': sum_count}

        # --- 讀取 Local Vote 資料 ---
        with open(file_path, 'r', encoding='utf-8') as f:
            local_data = json.load(f)
        
        final_output = {}

        # 針對該檔案的每一個 Source (例如 "中文發音")
        for src, targets in local_data.items():
            if not targets:
                continue

            # ==========================================
            # 步驟 1: 原始狀態計算 (Original Baseline)
            # ==========================================
            original_candidates = calculate_candidates_scores(src, targets, global_data, global_denominators)
            original_winner, _ = get_winner(original_candidates)

            # ==========================================
            # 步驟 2: Leave-One-Out 測試 (Stability Test)
            # ==========================================
            loo_results = {}
            
            # 針對每一個「有出現過」的 target，試著把它減 1
            for remove_target in targets.keys():
                # 深拷貝，確保不影響原始資料
                temp_targets = copy.deepcopy(targets)
                
                # 執行減 1
                if temp_targets[remove_target] > 0:
                    temp_targets[remove_target] -= 1
                
                # 如果減完變 0，通常我們會把它從候選名單移除 (或者保留但 count=0)
                # 這裡選擇移除，模擬「這個樣本從未存在」
                if temp_targets[remove_target] == 0:
                    del temp_targets[remove_target]
                
                # 如果全部都被刪光了 (原本只有1個樣本，減完變0)
                if not temp_targets:
                    loo_results[f"remove_{remove_target}"] = {
                        "removed_target": remove_target,
                        "new_winner": None,
                        "is_stable": False,
                        "note": "Data became empty"
                    }
                    continue

                # 重新計算分數
                new_candidates = calculate_candidates_scores(src, temp_targets, global_data, global_denominators)
                new_winner, new_score = get_winner(new_candidates)
                
                # 記錄結果
                loo_results[f"remove_{remove_target}"] = {
                    "removed_target": remove_target,
                    "new_winner": new_winner,
                    "is_stable": (new_winner == original_winner), # 關鍵指標：贏家有沒有換人？
                    "winner_local_score": new_score
                }

            # ==========================================
            # 步驟 3: 組合最終結構
            # ==========================================
            final_output[src] = {
                "original_candidates": original_candidates,
                "original_winner": original_winner,
                "loo_test_results": loo_results
            }

        # 輸出結果
        output_filename = f"{file_id}_LOO_analysis.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
            
        print(f"   ✅ 已輸出: {output_filename}")

    print("\n🎉 所有檔案 LOO 分析完成！")

if __name__ == "__main__":
    main()
