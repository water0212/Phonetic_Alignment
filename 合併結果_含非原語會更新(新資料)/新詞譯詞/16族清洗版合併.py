import json
import os
import glob

# --- 設定區 ---
# 放 JSON 檔案的資料夾名稱
INPUT_FOLDER = '16族_中借詞_清洗版'
# 輸出的檔案名稱
OUTPUT_FILE = '16族合併(未分族).json'

def merge_json_files():
    # 取得目前腳本的路徑
    base_path = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(base_path, INPUT_FOLDER)
    output_path = os.path.join(base_path, OUTPUT_FILE)

    # 檢查資料夾是否存在
    if not os.path.exists(folder_path):
        print(f"❌ 錯誤：找不到資料夾 '{INPUT_FOLDER}'。請建立資料夾並放入 JSON 檔案。")
        return

    # 搜尋所有 .json 檔案
    json_files = glob.glob(os.path.join(folder_path, "*.json"))
    
    if not json_files:
        print(f"⚠️  在 '{INPUT_FOLDER}' 裡面找不到任何 .json 檔案。")
        return

    print(f"🔍 找到 {len(json_files)} 個 JSON 檔案，開始合併...")

    merged_data = {}
    file_count = 0

    for file_path in json_files:
        filename = os.path.basename(file_path)
        
        # 避免讀取到之前的輸出檔（如果輸出檔不小心也在同個資料夾）
        if filename == OUTPUT_FILE:
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for key, value in data.items():
                    # 如果這個詞已經存在於合併資料中 (Key Collision)
                    if key in merged_data:
                        # 策略：保留原有的，並將新的 new_word 列表附加進去
                        # 這樣可以避免資料遺失 (例如不同檔案有不同的拼音或方言)
                        existing_entry = merged_data[key]
                        new_entries = value.get("new_word", [])
                        
                        # 將新的 new_word 內容加到舊的後面
                        existing_entry["new_word"].extend(new_entries)
                        
                        # (選用) 更新 source_year，這裡示範保留最新的或串接
                        # existing_entry["source_year"] = value.get("source_year", existing_entry["source_year"])
                        
                    else:
                        # 如果是新詞，直接加入
                        merged_data[key] = value
            
            print(f"  ✅ 已處理: {filename}")
            file_count += 1

        except Exception as e:
            print(f"  ❌ 處理 {filename} 時發生錯誤: {e}")

    # 寫入結果
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=4)
        
        print("-" * 30)
        print(f"🎉 合併完成！")
        print(f"共處理檔案數: {file_count}")
        print(f"總詞彙量: {len(merged_data)}")
        print(f"輸出檔案: {output_path}")
        
    except Exception as e:
        print(f"寫入輸出檔案時發生錯誤: {e}")

if __name__ == "__main__":
    merge_json_files()
