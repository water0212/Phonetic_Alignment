import json
import os
import glob

# === 修改 1: 在列表中加入 "0c" 和 "0v"，讓它們有位置可以存放 ===
order = [
    "b", "p", "m", "f", "d", "t", "n", "l",
    "g", "k", "h", "j", "q", "x", "zh", "ch",
    "sh", "r", "z", "c", "s", "0c",  # <--- 加入 0c (零聲母)
    "an", "en", "ang", "eng", "er",
    "i", "u", "ㄩ",
    "a", "o", "ㄜ", "e",
    "ai", "ei", "ao", "ou",
    "ia", "io", "ie", "iai", "iao", "iou",
    "ian", "in", "iang", "ing",
    "ua", "uo", "uai", "uei", "uan", "un", "uang", "ong",
    "ㄩe", "ㄩan", "ㄩn", "iong", "0v" # <--- 加入 0v (零韻母/空韻)
]

def vote_alignment_individual():
    # === 設定路徑 ===
    base_path = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_path, 'Refined_Excel')
    output_dir = os.path.join(base_path, '16族發音統計結果')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"已建立輸出資料夾: {output_dir}")

    if not os.path.exists(input_dir):
        print(f"錯誤: 找不到資料夾 {input_dir}")
        return

    # === 開始遍歷 01 到 16 ===
    for i in range(1, 17):
        group_id = f"{i:02d}"
        
        # 初始化投票箱
        vote_count = {k: {} for k in order}
        
        file_pattern = os.path.join(input_dir, f"refined_{group_id}_*_中借與音譯詞.json")
        found_files = glob.glob(file_pattern)

        if not found_files:
            print(f"[{group_id}] 找不到對應檔案，跳過。")
            continue

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

                        # === 修改 2: 處理聲母 (包含 0c) ===
                        # 邏輯：如果漢語聲母是 None 或空字串，視為 "0c"
                        target_ch_initial = initial_ch if initial_ch and initial_ch.strip() else "0c"
                        
                        # 確保這個聲母在我們的 order 列表中才統計 (避免髒資料)
                        if target_ch_initial in vote_count:
                            # 處理族語對應：如果是 None，視為 "0c"
                            t_init = tsou_initial if tsou_initial is not None else "0c"
                            t_init = t_init.strip()
                            if t_init == "": t_init = "0c"

                            # 移除原本的過濾條件，現在允許統計 0c -> 0c 或 0c -> ?
                            if t_init not in vote_count[target_ch_initial]:
                                vote_count[target_ch_initial][t_init] = 0
                            vote_count[target_ch_initial][t_init] += 1

                        # === 修改 3: 處理韻母 (包含 0v) ===
                        # 邏輯：如果漢語韻母是 None 或空字串，視為 "0v"
                        target_ch_final = final_ch if final_ch and final_ch.strip() else "0v"

                        if target_ch_final in vote_count:
                            # 處理族語對應
                            t_final = tsou_final if tsou_final is not None else "0v"
                            t_final = t_final.strip()
                            if t_final == "": t_final = "0v"

                            # 移除過濾，允許統計 0v
                            if t_final not in vote_count[target_ch_final]:
                                vote_count[target_ch_final][t_final] = 0
                            vote_count[target_ch_final][t_final] += 1

        # 輸出結果
        output_filename = f"{group_id}_output_alignment_voted.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(vote_count, f, ensure_ascii=False, indent=4)
        
        print(f"[{group_id}] 統計完成，已儲存至: {output_filename}")

if __name__ == "__main__":
    vote_alignment_individual()
