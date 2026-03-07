import json
import os

VOTE_FOLDER_NAME = '16族發音統計結果'
# 設定 Global 檔案前綴
GLOBAL_STATS_PREFIX = 'global_statistics_exclude_' 
DICT_FOLDER_NAME = 'fm_dict' 

# 權重設定
RANK_WEIGHT = 0.7
COUNT_WEIGHT = 0.3

def calculate_i_score(src, tgt, global_data, global_denominators):
    """
    輔助函式：計算全域分數 i
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

def is_target_contained_in_sentences(target, dict_data):
    """
    檢查候選發音字串是否包含在該族詞典的 fm_sentence 中
    """
    if not target: return False
    for word_entries in dict_data.values():
        for entry in word_entries:
            senses = entry.get('sense', [])
            for s in senses:
                examples = s.get('example', [])
                for ex in examples:
                    sentence = ex.get('fm_sentence', '')
                    if target in sentence:
                        return True
    return False

def main():
    # 1. 設定路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 假設資料夾與程式在同一層
    vote_dir = os.path.join(os.path.dirname(current_dir), VOTE_FOLDER_NAME)
    dict_dir = os.path.join(os.path.dirname(current_dir), DICT_FOLDER_NAME)

    if not os.path.exists(vote_dir):
        print(f"❌ 錯誤: 找不到 vote 資料夾 {vote_dir}")
        return

    # 2. 遍歷 vote 資料夾中的所有 JSON
    vote_files = [f for f in os.listdir(vote_dir) if f.endswith('.json')]
    print(f"📂 找到 {len(vote_files)} 個檔案，開始計算分數...")

    for filename in vote_files:
        file_path = os.path.join(vote_dir, filename)
        
        # --- 取得檔案編號 (例如 "01") ---
        file_id = filename.split('_')[0] 
        
        # --- 讀取對應的 Global Statistics (Leave-One-Out) ---
        global_filename = f"{GLOBAL_STATS_PREFIX}{file_id}.json"
        # 優先找 vote_coefficient 資料夾
        global_stats_path = os.path.join(current_dir, "global_statistics", global_filename)
        
        # 如果找不到，找當前目錄
        if not os.path.exists(global_stats_path):
             global_stats_path = os.path.join(current_dir, global_filename)

        if not os.path.exists(global_stats_path):
            print(f"⚠️ 警告: 找不到對應的 Global 檔 {global_filename}，跳過 {filename}")
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

        # --- 讀取對應詞典 ---
        dict_data = None
        if os.path.exists(dict_dir):
            dict_filename = next((f for f in os.listdir(dict_dir) if f.startswith(f"{file_id}_ilrdf_dict")), None)
            if dict_filename:
                with open(os.path.join(dict_dir, dict_filename), 'r', encoding='utf-8') as f:
                    dict_data = json.load(f)

        # --- 讀取本地 Vote 資料 ---
        with open(file_path, 'r', encoding='utf-8') as f:
            local_data = json.load(f)
        
        processed_data = {}

        # 針對該檔案的每一個 Source
        for src, targets in local_data.items():
            temp_results = []

            # ==========================================
            # 情況 A: 本地有資料 (Local Data Exists)
            # ==========================================
            if targets:
                local_total_count = sum(targets.values())

                # 只遍歷「本地有出現過」的 targets
                for tgt, count in targets.items():
                    k_score = count / local_total_count if local_total_count > 0 else 0
                    i_score = calculate_i_score(src, tgt, global_data, global_denominators)

                    temp_results.append({
                        'target': tgt,
                        'local_count': count,
                        'global_i': i_score,
                        'data': {
                            'local_count': count, 
                            'local_score_k': round(k_score, 4),
                            'global_score_i': round(i_score, 4),
                            'note': 'Local Vote'
                        }
                    })
                
                # 排序：先比 local_count (大到小)，再比 global_i (大到小)
                temp_results.sort(key=lambda x: (x['local_count'], x['global_i']), reverse=True)
                
                # 【重點】這裡不切片，保留所有本地有票的候選者

            # ==========================================
            # 情況 B: 本地無資料 (No Local Data) -> 查 Global
            # ==========================================
            else:
                if src in global_data and global_data[src]:
                    candidates = []
                    for g_tgt in global_data[src]:
                        current_i = calculate_i_score(src, g_tgt, global_data, global_denominators)
                        candidates.append((g_tgt, current_i))
                    
                    # 依全域分數由高到低排序
                    candidates.sort(key=lambda x: x[1], reverse=True)

                    best_target = None
                    max_i_score = -1.0

                    # 尋找第一個「出現在語料中」的發音
                    for g_tgt, g_i in candidates:
                        if dict_data is None or is_target_contained_in_sentences(g_tgt, dict_data):
                            best_target = g_tgt
                            max_i_score = g_i
                            break 
                    
                    # 兜底：如果都沒符合，選全域第一名
                    if best_target is None and candidates:
                        best_target, max_i_score = candidates[0]

                    if best_target is not None:
                        temp_results.append({
                            'target': best_target,
                            'local_count': 0,
                            'global_i': max_i_score,
                            'data': {
                                'local_count': 0,
                                'local_score_k': 0.0,
                                'global_score_i': round(max_i_score, 4),
                                'note': 'Auto-filled from Global'
                            }
                        })

            # --- 重組回字典格式 ---
            processed_data[src] = {}
            for item in temp_results:
                processed_data[src][item['target']] = item['data']

        # 5. 輸出結果
        output_path = os.path.join(current_dir, filename) 
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=4)
            
        status = "已校驗" if dict_data else "無字典可參考"
        print(f"   ✅ 已輸出: {filename} (Local優先/Global補缺) | {status}")

    print("\n🎉 所有檔案處理完成！")

if __name__ == "__main__":
    main()
