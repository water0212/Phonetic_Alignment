import json
import os
import glob

# 保持原本的順序列表
order = [
    "b", "p", "m", "f", "d", "t", "n", "l",
    "g", "k", "h", "j", "q", "x", "zh", "ch",
    "sh", "r", "z", "c", "s",
    "an", "en", "ang", "eng", "er",
    "i", "u", "u:",
    "a", "o", "ㄜ", "e",
    "ai", "ei", "ao", "ou",
    "ia", "io", "ie", "iai", "iao", "iou",
    "ian", "in", "iang", "ing",
    "ua", "uo", "uai", "uei", "uan", "un", "uang", "ong",
    "u:e", "u:an", "u:n", "iong"
]

def vote_alignment_individual():
    # === 設定路徑 ===
    base_path = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_path, 'Refined_Excel')
    output_dir = os.path.join(base_path, '16族發音統計結果') # 建立一個專門放結果的資料夾

    # 如果輸出資料夾不存在，則建立
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"已建立輸出資料夾: {output_dir}")

    # 確保輸入資料夾存在
    if not os.path.exists(input_dir):
        print(f"錯誤: 找不到資料夾 {input_dir}")
        return

    # === 開始遍歷 01 到 16 ===
    for i in range(1, 17):
        group_id = f"{i:02d}"  # 將數字轉為字串，如 "01", "05", "16"
        
        # === 關鍵修改 1: 每次迴圈開始時，初始化一個全新的投票箱 ===
        vote_count = {k: {} for k in order}
        
        # 搜尋對應編號的檔案
        file_pattern = os.path.join(input_dir, f"refined_{group_id}_*_中借與音譯詞.json")
        found_files = glob.glob(file_pattern)

        if not found_files:
            print(f"[{group_id}] 找不到對應檔案，跳過。")
            continue

        # 通常每個編號只有一個檔案，但 glob 回傳的是列表，所以用迴圈讀取
        for file_path in found_files:
            file_name = os.path.basename(file_path)
            print(f"[{group_id}] 正在處理: {file_name}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    print(f"  -> 錯誤: JSON 格式損毀，跳過此檔")
                    continue

            # === 統計該檔案的數據 ===
            for item in data:
                alignments = item.get('alignment', [])
                if not alignments:
                    continue
                
                # 過濾條件：若含有「族語缺失」，則整單字不參與投票
                has_missing_tsou = any(align.get('status') == "族語缺失" for align in alignments)
                if has_missing_tsou:
                    continue

                # 開始投票
                for alignment in alignments:
                    status = alignment.get('status')
                    if status in ["已匹配", "已匹配(合併)"]:
                        ch = alignment.get('chinese_syllable')
                        tsou = alignment.get('tsou_syllable')
                        
                        if not ch or not tsou: continue

                        initial_ch = ch.get('initial')
                        final_ch = ch.get('final')
                        tsou_initial = tsou.get('initial')
                        tsou_final = tsou.get('final')

                        # 統計聲母
                        if initial_ch:
                            if initial_ch not in vote_count:
                                vote_count[initial_ch] = {} # 防呆：若遇到不在 order 裡的聲母
                            if tsou_initial not in vote_count[initial_ch]:
                                vote_count[initial_ch][tsou_initial] = 0
                            vote_count[initial_ch][tsou_initial] += 1

                        # 統計韻母
                        if final_ch:
                            if final_ch not in vote_count:
                                vote_count[final_ch] = {} # 防呆
                            if tsou_final not in vote_count[final_ch]:
                                vote_count[final_ch][tsou_final] = 0
                            vote_count[final_ch][tsou_final] += 1

        # === 關鍵修改 2: 處理完該組 (01~16) 後，立刻輸出獨立檔案 ===
        output_filename = f"{group_id}_output_alignment_voted.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(vote_count, f, ensure_ascii=False, indent=4)
        
        print(f"[{group_id}] 統計完成，已儲存至: {output_filename}")

if __name__ == "__main__":
    vote_alignment_individual()
