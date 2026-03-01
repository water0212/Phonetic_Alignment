import json
import os

VOTE_FOLDER_NAME = 'ailgn_syllables/16族發音統計結果'
GLOBAL_STATS_FILENAME = 'global_statistics.json'
# 假設詞典檔案放在與此程式同層的 'Dictionaries' 資料夾中
DICT_FOLDER_NAME = 'fm_dict' 

# 權重設定 (僅用於計算 i 分數供參考，不影響第一順位排序)
RANK_WEIGHT = 0.7
COUNT_WEIGHT = 0.3

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
    
    return (part_rank * RANK_WEIGHT) + (part_count * COUNT_WEIGHT)

def is_target_contained_in_sentences(target, dict_data):
    """
    新功能：檢查候選發音字串是否包含在該族詞典的 fm_sentence 中
    針對詞典格式：詞彙 -> sense(list) -> example(list) -> fm_sentence 進行解析
    """
    if not target: return False
    
    # 遍歷詞典中每一個單詞項 (dict_data 的 values 是 list)
    for word_entries in dict_data.values():
        # word_entries 是一個 list，裡面包含多個 sense
        for entry in word_entries:
            # 取得 sense 裡面的 example list
            senses = entry.get('sense', [])
            for s in senses:
                examples = s.get('example', [])
                # 遍歷所有的例句
                for ex in examples:
                    sentence = ex.get('fm_sentence', '')
                    # 只要包含子字串就回傳 True
                    if target in sentence:
                        return True
    return False
def main():
    # 1. 設定路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 往上一層找 vote 資料夾
    vote_dir = os.path.join(os.path.dirname(current_dir), VOTE_FOLDER_NAME)
    
    # global_statistics.json 就在本程式旁邊
    global_stats_path = os.path.join(current_dir, GLOBAL_STATS_FILENAME)

    # 詞典資料夾路徑
    dict_dir = os.path.join(os.path.dirname(current_dir), DICT_FOLDER_NAME)

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
        
        # --- 新增：根據檔名編號讀取對應詞典 ---
        file_id = filename.split('_')[0] # 取得編號如 "01"
        dict_data = None
        if os.path.exists(dict_dir):
            # 尋找開頭為 "01_ilrdf_dict" 的檔案
            dict_filename = next((f for f in os.listdir(dict_dir) if f.startswith(f"{file_id}_ilrdf_dict")), None)
            if dict_filename:
                with open(os.path.join(dict_dir, dict_filename), 'r', encoding='utf-8') as f:
                    dict_data = json.load(f)
        # --------------------------------

        with open(file_path, 'r', encoding='utf-8') as f:
            local_data = json.load(f)
        
        processed_data = {}

        # 針對該檔案的每一個 Source (例如 "b", "o")
        for src, targets in local_data.items():
            temp_results = []

            # 情況 A: 本地有資料 
            if targets:
                local_total_count = sum(targets.values())

                for tgt, count in targets.items():
                    # 計算 k (個別分數 - 僅供參考)
                    k_score = count / local_total_count if local_total_count > 0 else 0

                    # 計算 i (全域分數 - 用於同票時的第二順位)
                    i_score = calculate_i_score(src, tgt, global_data, global_denominators)

                    # 計算總分 (僅供參考，不影響排序)
                    total_score = k_score + i_score

                    temp_results.append({
                        'target': tgt,
                        'local_count': count,    # [關鍵] 加入原始次數用於排序
                        'global_i': i_score,     # [關鍵] 加入全域分數用於排序
                        'data': {
                            'local_count': count, # 順便把次數寫進結果，方便查看
                            'local_score_k': round(k_score, 4),
                            'global_score_i': round(i_score, 4),
                            'total_score': round(total_score, 4)
                        }
                    })
                
                # --- [修改重點] 排序邏輯 ---
                # 1. 先比 local_count (由大到小)
                # 2. 如果次數一樣，再比 global_i (由大到小)
                temp_results.sort(key=lambda x: (x['local_count'], x['global_i']), reverse=True)

            # 情況 B: 本地無資料 (維持原樣，完全依賴 Global)
            else:
                if src in global_data and global_data[src]:
                    # 先將該 Source 下的所有全域候選者按 i 分數排序
                    candidates = []
                    for g_tgt in global_data[src]:
                        current_i = calculate_i_score(src, g_tgt, global_data, global_denominators)
                        candidates.append((g_tgt, current_i))
                    
                    # 依全域分數由高到低排序
                    candidates.sort(key=lambda x: x[1], reverse=True)

                    best_target = None
                    max_i_score = -1.0

                    # 依序尋找第一個「出現在語料中」的發音
                    for g_tgt, g_i in candidates:
                        # 只要 target 字串包含在任何 fm_sentence 中即可
                        if dict_data is None or is_target_contained_in_sentences(g_tgt, dict_data):
                            best_target = g_tgt
                            max_i_score = g_i
                            break
                    
                    # 如果循環完都沒符合的（雖然機率低），則退而求其次選全域第一名
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
                                'total_score': round(max_i_score, 4),
                                'note': 'Auto-filled from Global (Contained in Dict)'
                            }
                        })

            # --- 重組回字典格式 ---
            # 因為 Python 3.7+ 的字典是有序的，這裡寫入的順序就是剛剛排序好的順序 (第一名在最前面)
            processed_data[src] = {}
            for item in temp_results:
                processed_data[src][item['target']] = item['data']

        # 5. 輸出結果
        output_path = os.path.join(current_dir, filename) 
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=4)
            
        status = "已校驗" if dict_data else "無字典可參考"
        print(f"   ✅ 已輸出: {filename} ({status})")

    print("🎉 所有檔案處理完成！填補邏輯：分數優先且需字串包含於詞典句子中。")

if __name__ == "__main__":
    main()