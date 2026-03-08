import json
import os
import copy

# === 設定區 ===
VOTE_FOLDER_NAME = '16族發音統計結果'
GLOBAL_STATS_PREFIX = 'global_statistics_exclude_' 
DICT_FOLDER_NAME = 'fm_dict' 
OUTPUT_FOLDER_NAME = '16族最終權重結果_LOO測試' 

# 權重設定 (用於計算 Global Score)
RANK_WEIGHT = 0.7
COUNT_WEIGHT = 0.3

def calculate_i_score(src, tgt, global_data, global_denominators):
    """ 計算全域分數 i """
    if src not in global_data or tgt not in global_data[src]:
        return 0.0
    
    g_stats = global_data[src][tgt] # [rank, count]
    g_rank = g_stats[0]
    g_count = g_stats[1]
    
    denoms = global_denominators.get(src, {'sum_rank': 0, 'sum_count': 0})
    sum_rank = denoms['sum_rank']
    sum_count = denoms['sum_count']

    part_rank = (g_rank / sum_rank) if sum_rank > 0 else 0
    part_count = (g_count / sum_count) if sum_count > 0 else 0
    
    return (part_rank * RANK_WEIGHT) + (part_count * COUNT_WEIGHT)

def calculate_candidates_scores(src, current_targets, global_data, global_denominators):
    """ 計算候選人分數 """
    candidates = {}
    local_total_count = sum(current_targets.values())

    for tgt, count in current_targets.items():
        k_score = count / local_total_count if local_total_count > 0 else 0
        i_score = calculate_i_score(src, tgt, global_data, global_denominators)
        
        candidates[tgt] = {
            'local_count': count,
            'local_score_k': round(k_score, 4),
            'global_score_i': round(i_score, 4)
        }
    return candidates

def get_winner(candidates_dict):
    """ 決定贏家 (若 Local 平手，則看 Global) """
    if not candidates_dict:
        return None, 0
    items = list(candidates_dict.items())
    # 排序：先比 Local Count，再比 Global Score
    items.sort(key=lambda x: (x[1]['local_count'], x[1]['global_score_i']), reverse=True)
    return items[0][0], items[0][1]['local_score_k']

def check_is_tie(candidates_dict):
    """ 
    【新增功能】檢查是否平票 (只看 Local Count) 
    回傳: True (平手) / False (有唯一贏家)
    """
    if not candidates_dict:
        return False
    
    # 取出所有人的 local_count
    counts = [data['local_count'] for data in candidates_dict.values()]
    
    if not counts:
        return False
        
    max_count = max(counts)
    # 計算有幾個人拿到最高票
    winners_count = counts.count(max_count)
    
    return winners_count > 1

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    vote_dir = os.path.join(os.path.dirname(current_dir), VOTE_FOLDER_NAME)
    output_dir = os.path.join(current_dir, OUTPUT_FOLDER_NAME)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not os.path.exists(vote_dir):
        print(f"❌ 錯誤: 找不到 vote 資料夾 {vote_dir}")
        return

    vote_files = [f for f in os.listdir(vote_dir) if f.endswith('.json')]
    print(f"📂 找到 {len(vote_files)} 個檔案，開始執行 LOO 分析 (含平票檢測)...")

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

        for src, targets in local_data.items():
            if not targets:
                continue

            # 1. 原始狀態
            original_candidates = calculate_candidates_scores(src, targets, global_data, global_denominators)
            original_winner, _ = get_winner(original_candidates)
            original_is_tie = check_is_tie(original_candidates) # 原始狀態是否平手

            # 2. Leave-One-Out 測試
            loo_results = {}
            
            for remove_target in targets.keys():
                temp_targets = copy.deepcopy(targets)
                
                if temp_targets[remove_target] > 0:
                    temp_targets[remove_target] -= 1
                
                if temp_targets[remove_target] == 0:
                    del temp_targets[remove_target]
                
                if not temp_targets:
                    loo_results[f"remove_{remove_target}"] = {
                        "removed_target": remove_target,
                        "new_winner": None,
                        "is_tie": False,
                        "is_stable": False,
                        "note": "Data became empty"
                    }
                    continue

                # 重新計算
                new_candidates = calculate_candidates_scores(src, temp_targets, global_data, global_denominators)
                new_winner, new_score = get_winner(new_candidates)
                
                # 【新增】檢查是否平票
                is_tie = check_is_tie(new_candidates)
                
                loo_results[f"remove_{remove_target}"] = {
                    "removed_target": remove_target,
                    "new_winner": new_winner,
                    "is_tie": is_tie,  # <--- 新增欄位
                    "is_stable": (new_winner == original_winner),
                    "winner_local_score": new_score
                }

            final_output[src] = {
                "original_stats": original_candidates,
                "original_winner": original_winner,
                "original_is_tie": original_is_tie, # 也記錄原始是否平手
                "loo_test_results": loo_results
            }

        output_filename = f"{file_id}_LOO_analysis.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
            
        print(f"   ✅ 已輸出: {output_filename}")

    print("\n🎉 分析完成！")

if __name__ == "__main__":
    main()
