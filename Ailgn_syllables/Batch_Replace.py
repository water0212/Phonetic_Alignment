import json
import os

# ==========================================
# 🔧 設定區域：在這裡新增你要替換的規則
# 格式： "舊的字": "新的字"
# ==========================================
REPLACEMENT_RULES = {
    "ē": "é",      # 範例：修正母音
    # "舊": "新",   # 你可以在這裡無限新增
}

# ==========================================
# 📂 檔案路徑設定
# ==========================================
# 這裡沿用你之前的族語列表
TRIBES = [
    "阿美語", "泰雅語", "排灣語", "布農語", "卑南語", "魯凱語", "鄒語",
    "賽夏語", "雅美語", "邵語", "噶瑪蘭語", "太魯閣語", "撒奇萊雅語", 
    "賽德克語", "拉阿魯哇語", "卡那卡那富語"
]

def apply_replacements(text):
    """將文字依照規則進行替換"""
    if not isinstance(text, str):
        return text
    
    original_text = text
    for old_str, new_str in REPLACEMENT_RULES.items():
        if old_str in text:
            text = text.replace(old_str, new_str)
    
    return text, (text != original_text)

def recursive_replace(data, counter):
    """遞迴遍歷 JSON 資料並替換所有字串值"""
    if isinstance(data, dict):
        # 如果是字典，遍歷每一個 key-value
        for key, value in data.items():
            # 遞迴處理 value
            data[key] = recursive_replace(value, counter)
    
    elif isinstance(data, list):
        # 如果是列表，遍歷每一個元素
        for i in range(len(data)):
            data[i] = recursive_replace(data[i], counter)
    
    elif isinstance(data, str):
        # 如果是字串，執行替換
        new_text, changed = apply_replacements(data)
        if changed:
            counter["count"] += 1
        return new_text
    
    return data

def main():
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    print(f"開始執行批量替換... 目前設定了 {len(REPLACEMENT_RULES)} 條規則。")
    print("-" * 30)

    # for index, tribe in enumerate(TRIBES):
    #     folder_name = f"{index+1:02d}{tribe}"
    #     file_path = os.path.join(base_path, folder_name, "merged_output.json")
        
    #     if not os.path.exists(file_path):
    #         # print(f"跳過: 找不到 {file_path}")
    #         continue

    #     try:
    #         # 1. 讀取檔案
    #         with open(file_path, 'r', encoding='utf-8') as f:
    #             data = json.load(f)
            
    #         # 2. 執行替換
    #         counter = {"count": 0} # 使用字典來傳遞計數器
    #         new_data = recursive_replace(data, counter)
            
    #         # 3. 如果有變更，才寫回檔案
    #         if counter["count"] > 0:
    #             with open(file_path, 'w', encoding='utf-8') as f:
    #                 json.dump(new_data, f, ensure_ascii=False, indent=4)
    #             print(f"✅ {tribe}: 已修正 {counter['count']} 處內容")
    #         else:
    #             print(f"⚪ {tribe}: 無需變更")

    #     except Exception as e:
    #         print(f"❌ {tribe} 發生錯誤: {e}")
    
    file_path = os.path.join(base_path, "merged_output.json")

    try:
            # 1. 讀取檔案
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 2. 執行替換
        counter = {"count": 0} # 使用字典來傳遞計數器
        new_data = recursive_replace(data, counter)
            
        # 3. 如果有變更，才寫回檔案
        if counter["count"] > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=4)
            print(f"✅ {file_path}: 已修正 {counter['count']} 處內容")
        else:
            print(f"⚪ {file_path}: 無需變更")

    except Exception as e:
        print(f"❌ {file_path} 發生錯誤: {e}")

    print("-" * 30)
    print("所有作業完成！")

if __name__ == "__main__":
    main()
