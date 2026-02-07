import json
import os
import Syllable_decomposition01
# ==========================================
# 1. 來自 fix.py 的核心定義
# ==========================================
INITIALS = ['zh', 'ch', 'sh', 'b', 'p', 'm', 'f', 'd', 't', 'n', 'l', 
            'g', 'k', 'h', 'j', 'q', 'x', 'r', 'z', 'c', 's','w','y'] #補上w, y

# 關鍵：依照長度排序 (reverse=True)，確保 zh, ch, sh 能優先被匹配，而不是只匹配到 z, c, s
INITIALS.sort(key=len, reverse=True)

def split_syllable_by_initials(syllable):
    """
    依據 fix.py 的 INITIALS 列表進行切分。
    輸入: "sin"
    輸出: ("s", "in")
    """
    if not syllable:
        return "", ""

    syllable = syllable.lower()
    curr_initial = ""
    curr_final = syllable

    # 模擬 fix.py 的切分迴圈
    for ini in INITIALS:
        if syllable.startswith(ini):
            curr_initial = ini
            curr_final = syllable[len(ini):]
            break
    
    return curr_initial, curr_final

def model_main(input_file):
    input_data = Syllable_decomposition01.model_main(input_file)  # 先執行音節拆解，得到 "音節拆解.json" 的路徑
    # 檢查輸入檔是否存在

    data = json.loads(input_data)

    # 處理每個單字
    for entry in data:
        syllables = entry.get("syllables", [])
        structure_list = []
        
        for syl in syllables:
            ini, fin = split_syllable_by_initials(syl)
            
            # --- 修改重點：空值補 0c / 0v ---
            if not ini:  # 如果聲母是空字串
                ini = "0c"
            
            if not fin:  # 如果韻母是空字串
                fin = "0v"
            # ------------------------------

            # 建立顯示字串，例如 "s,in" 或 "0c,a"
            display_str = f"{ini},{fin}"
            
            structure_list.append({
                "original": syl,
                "initial": ini,
                "final": fin,
                "split_display": display_str
            })
        
        # 將拆解結果寫入該單字的資料中
        entry["syllable_structure"] = structure_list
    json_str = json.dumps(data, ensure_ascii=False, indent=4)
    # print(f"處理完成！音節轉字典")
    return json_str


def main():
    # 檔案路徑設定
    arr = ["阿美語","泰雅語","排灣語","布農語","卑南語","魯凱語","鄒語",
       "賽夏語","雅美語","邵語","噶瑪蘭語","太魯閣語","撒奇萊雅語","賽德克語","拉阿魯哇語","卡那卡那富語",]
    for name in arr:
        base_path = r"C:\code\專題\畢業專題\新詞整合\新詞譯詞"
        new_path = r"C:\code\專題\畢業專題\data"
        os.makedirs(os.path.join(os.path.join(new_path, f"{arr.index(name)+1:02d}{name}")), exist_ok=True)
        input_file = os.path.join(base_path, f"{arr.index(name)+1:02d}{name}", "音節拆解.json")
        output_file = os.path.join(new_path, f"{arr.index(name)+1:02d}{name}", "音節轉字典.json")

        # 檢查輸入檔是否存在
        if not os.path.exists(input_file):
            print(f"錯誤: 找不到輸入檔案 {input_file}")
            continue

        print(f"正在讀取檔案: {input_file} ...")

        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 處理每個單字
        for entry in data:
            syllables = entry.get("syllables", [])
            structure_list = []
            
            for syl in syllables:
                ini, fin = split_syllable_by_initials(syl)
                
                # --- 修改重點：空值補 0c / 0v ---
                if not ini:  # 如果聲母是空字串
                    ini = "0c"
                
                if not fin:  # 如果韻母是空字串
                    fin = "0v"
                # ------------------------------

                # 建立顯示字串，例如 "s,in" 或 "0c,a"
                display_str = f"{ini},{fin}"
                
                structure_list.append({
                    "original": syl,
                    "initial": ini,
                    "final": fin,
                    "split_display": display_str
                })
            
            # 將拆解結果寫入該單字的資料中
            entry["syllable_structure"] = structure_list

        # 寫入新的 JSON 檔案
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            print(f"處理完成！")
            print(f"已輸出詳細拆解檔案至: {output_file}")
            
            # 顯示範例結果
            # if data:
            #     example = data[0]
            #     print("\n--- 範例輸出 ---")
            #     print(f"單字: {example['amis_word']}")
            #     print(f"音節: {example['syllables']}")
            #     print("拆解結果:")
            #     for item in example['syllable_structure']:
            #         print(f"  {item['original']} -> {item['split_display']} (聲母: '{item['initial']}', 韻母: '{item['final']}')")

        except Exception as e:
            print(f"寫入檔案時發生錯誤: {e}")

if __name__ == "__main__":
    main()
