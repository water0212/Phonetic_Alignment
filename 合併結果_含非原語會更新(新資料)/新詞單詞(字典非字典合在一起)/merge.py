import json
import glob
import os
import sys
import re  # 引入正規表達式模組，用來抓年份

def extract_year_from_filename(filename):
    """
    從檔名中嘗試提取年份 (針對民國 100-119 年)
    例如: "16卡那卡那富語104.json" -> 回傳 "104"
    若找不到，則回傳完整檔名。
    """
    # 搜尋 100 ~ 119 的數字
    match = re.search(r'(1[0-1]\d)', filename)
    if match:
        return match.group(1)
    
    # 如果找不到 3 位數年份，嘗試找 2 位數 (例如 99, 98)
    match_old = re.search(r'(9\d)', filename)
    if match_old:
        return match_old.group(1)
        
    # 真的找不到，就回傳檔名當作來源
    return filename

def process_single_folder(folder_path):
    folder_name = os.path.basename(folder_path)
    print(f"🔄 正在處理資料夾: [{folder_name}] ...")

    output_file = os.path.join(folder_path, 'merged_output.json')
    log_file = os.path.join(folder_path, 'duplicates_log.json')

    search_pattern = os.path.join(folder_path, '*.json')
    json_files = glob.glob(search_pattern)

    files_to_ignore = {os.path.abspath(output_file), os.path.abspath(log_file)}
    json_files = [f for f in json_files if os.path.abspath(f) not in files_to_ignore]

    if not json_files:
        print(f"   ⚠️  [{folder_name}] 裡面沒有 JSON 檔案，跳過。")
        return

    merged_data = {}
    duplicates_data = {}

    # 為了確保年份順序，我們可以先對檔名排序 (讓 104 先跑，105 後跑)
    json_files.sort()

    for file_path in json_files:
        current_file_name = os.path.basename(file_path)
        
        # ★ 取得年份標籤
        year_tag = extract_year_from_filename(current_file_name)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content: continue
                
                data = json.loads(content)
                
                if isinstance(data, dict):
                    for key, value in data.items():
                        
                        # ★ 在資料內容中注入年份標籤
                        # 確保 value 是字典才能寫入
                        if isinstance(value, dict):
                            value["source_year"] = year_tag

                        # --- 重複檢查 ---
                        if key in merged_data:
                            if current_file_name not in duplicates_data:
                                duplicates_data[current_file_name] = {}
                            duplicates_data[current_file_name][key] = value
                            continue 
                        
                        # --- 格式補全 ---
                        if isinstance(value, dict) and "new_word" in value:
                            new_word_list = value["new_word"]
                            if isinstance(new_word_list, list):
                                for item in new_word_list:
                                    if isinstance(item, dict):
                                        if "dialect" not in item:
                                            item["dialect"] = []
                        
                        # --- 加入合併 ---
                        merged_data[key] = value

        except Exception as e:
            print(f"   ❌ 讀取 {current_file_name} 失敗: {e}")

    # --- 輸出合併檔 ---
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=4)
        print(f"   ✅ 合併成功！產生: merged_output.json (共 {len(merged_data)} 筆)")
    except Exception as e:
        print(f"   ❌ 存檔失敗: {e}")

    # --- 輸出重複紀錄檔 ---
    if duplicates_data:
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(duplicates_data, f, ensure_ascii=False, indent=4)
            dup_count = sum(len(v) for v in duplicates_data.values())
            print(f"   ⚠️  發現 {dup_count} 筆重複，已記錄於: duplicates_log.json")
        except Exception as e:
            print(f"   ❌ 重複紀錄存檔失敗: {e}")

def main():
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    print(f"📍 根目錄: {base_path}")
    print("🚀 開始掃描子資料夾 (含年份標註)...\n" + "="*40)

    subfolders = [f.path for f in os.scandir(base_path) if f.is_dir() and not f.name.startswith('.')]

    if not subfolders:
        print("❌ 找不到任何子資料夾！")
        input("按 Enter 結束...")
        return

    for folder in subfolders:
        process_single_folder(folder)
        print("-" * 40)

    print("\n🎉 全部處理完成！")
    input("按 Enter 結束程式...")

if __name__ == "__main__":
    main()
