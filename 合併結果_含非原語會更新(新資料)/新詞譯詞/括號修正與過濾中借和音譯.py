import json
import os
import re

# ==========================================
# 1. 設定路徑與參數
# ==========================================

# --- 修改重點：改用相對路徑 (自動抓取程式所在位置) ---
# 這樣就不會因為使用者名稱不同 (jimmy vs 小菜) 而報錯
ROOT_FOLDER = os.path.dirname(os.path.abspath(__file__))

# 新的輸出資料夾 (會建立在程式旁邊的資料夾)
NEW_OUTPUT_FOLDER = os.path.join(ROOT_FOLDER, "16族_中借詞_清洗版")

# 篩選關鍵字 加入音譯
LIST_CH = [
    '(中譯)', '(華語借詞)', '(音譯(中借))', '(漢譯)', '(中借)',
    '健保(中借)', '化學(中譯)肥料', '國有局(中譯)', '捷運(中借)',
    '水利局(中譯)', '華語直譯', '電腦(中譯)', '電腦網路 (中譯)',
    '高速公路(中借)', '高速鐵路(中借)', '中譯', '音譯', '音譯（縮略）',
    '(音譯詞)', '(sakalima) (音譯詞)', 'CD的音譯', '流籠(音譯)',
    '7-11 的音譯', '(Iencu mincu ui-enhui)(音譯詞)' 
]

# 族語代碼對照
LANG_MAP = {
    "01": "阿美語", "02": "泰雅語", "03": "排灣語", "04": "布農語",
    "05": "卑南語", "06": "魯凱語", "07": "鄒語", "08": "賽夏語",
    "09": "雅美語", "10": "邵語", "11": "噶瑪蘭語", "12": "太魯閣語",
    "13": "撒奇萊雅語", "14": "賽德克語", "15": "拉阿魯哇語", "16": "卡那卡那富語"
}

# ==========================================
# 2. 清洗邏輯函式
# ==========================================
def clean_chinese_key(word):
    """
    清洗中文詞：回傳 None 代表刪除；回傳字串代表清洗結果
    """
    if not word: return "未知詞"
    word = word.strip()

    # --- 1. 刪除黑名單 ---
    if word == "隨身碟(USB)" or word == "X光":
        return None

    # --- 2. 特殊取代 ---
    if word == "鄉(鎮、市)公所":
        return "市公所"
    if word == "小耳朵(天線)":
        return "天線"
    if word == "(電腦)網路":
        return "電腦"

    # --- 3. 移除括號及內容 ---
    # 先把括號拿掉，避免像 "電腦(Computer)" 因為 Computer 被刪除
    word = re.sub(r'\(.*?\)', '', word)
    word = re.sub(r'（.*?）', '', word)
    
    word = word.strip()

    # --- 4. [新增] 檢查是否包含英文或數字 ---
    # 如果清洗後的詞仍包含 A-Z, a-z, 0-9，則回傳 None (刪除該詞)
    if re.search(r'[a-zA-Z0-9]', word):
        return None

    return word

def clean_fm_symbol(new_word_list):
    """
    清洗族語詞 (fm_word) 中的符號：
    將直式引號 ' 替換為彎式引號 ’
    """
    if not new_word_list or not isinstance(new_word_list, list):
        return

    for item in new_word_list:
        if 'fm_word' not in item or not item['fm_word']:
            continue

        fm_word = item['fm_word']
        if isinstance(fm_word, str):
            # 將 ' 替換為 ’
            item['fm_word'] = fm_word.replace("'", "’")
        elif isinstance(fm_word, list):
            item['fm_word'] = [
                value.replace("'", "’") if isinstance(value, str) else value
                for value in fm_word
            ]

# ==========================================
# 3. 主程式邏輯
# ==========================================
def main():
    print(f"📂 根目錄 (程式所在位置): {ROOT_FOLDER}")
    
    if not os.path.exists(NEW_OUTPUT_FOLDER):
        try:
            os.makedirs(NEW_OUTPUT_FOLDER)
            print(f"📁 已建立新資料夾: {NEW_OUTPUT_FOLDER}")
        except PermissionError:
            print(f"❌ 權限錯誤：無法在 {ROOT_FOLDER} 建立資料夾。請確認您有寫入權限。")
            return

    files_processed = 0

    for root, dirs, files in os.walk(ROOT_FOLDER):
        
        # 避免遞迴讀取到剛剛建立的輸出資料夾
        if "16族_中借詞_清洗版" in root:
            continue

        for filename in files:
            if filename.endswith("_merged_output.json"):
                
                code = filename[:2]
                if code not in LANG_MAP:
                    continue

                lang_name = LANG_MAP[code]
                file_path = os.path.join(root, filename)
                
                print(f"\n➡️ 正在處理: {lang_name} ({filename})...")

                try:
                    # --- 步驟 A: 讀取原始檔案 ---
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    cleaned_data_to_save = None 
                    extraction_source_list = [] 

                    # --- 判斷資料型態 ---
                    if isinstance(data, dict):
                        new_dict = {}
                        for key, content in data.items():
                            new_key = clean_chinese_key(key)
                            if new_key is not None:
                                if isinstance(content, dict):
                                    content['chinese'] = new_key 
                                    clean_fm_symbol(content.get('new_word', []))
                                new_dict[new_key] = content
                                extraction_source_list.append(content)
                        cleaned_data_to_save = new_dict

                    elif isinstance(data, list):
                        new_list = []
                        for entry in data:
                            original_key = entry.get('chinese') or entry.get('word') or "未知詞"
                            new_key = clean_chinese_key(original_key)
                            if new_key is not None:
                                entry['chinese'] = new_key
                                clean_fm_symbol(entry.get('new_word', []))
                                new_list.append(entry)
                                extraction_source_list.append(entry)
                        cleaned_data_to_save = new_list
                    
                    else:
                        print(f"   ⚠️ 未知格式，跳過。")
                        continue

                    # --- 步驟 B: 保留原始 merged_output ---
                    # 清洗結果只用於輸出中借與音譯詞，不覆蓋同步後的 aggregate。
                    if cleaned_data_to_save:
                        print(f"   ✅ 已建立清洗暫存資料（未覆蓋原始檔案）")

                    # --- 步驟 C: 篩選中借詞並另存新檔 ---
                    extraction_dict = {}
                    extract_count = 0

                    for entry in extraction_source_list:
                        key = entry.get('chinese') or entry.get('word')
                        new_words = entry.get('new_word', [])
                        source_year = entry.get('source_year', '')

                        filtered_new_words = []
                        for item in new_words:
                            semantic = item.get('ch_semantic', '').strip()
                            if semantic in LIST_CH:
                                filtered_new_words.append(item)
                        
                        if filtered_new_words and key:
                            extraction_dict[key] = {
                                "new_word": filtered_new_words,
                                "source_year": source_year
                            }
                            extract_count += 1

                    if extract_count > 0:
                        new_filename = f"{code}_{lang_name}_中借與音譯詞.json"
                        new_file_path = os.path.join(NEW_OUTPUT_FOLDER, new_filename)
                        
                        with open(new_file_path, 'w', encoding='utf-8') as f:
                            json.dump(extraction_dict, f, ensure_ascii=False, indent=4)
                        
                        print(f"   ✨ 已提取 {extract_count} 筆 -> {new_filename}")
                        files_processed += 1
                    else:
                        print(f"   ⚠️ 無符合資料。")

                except Exception as e:
                    print(f"❌ 錯誤: {e}")

    print("\n" + "="*30)
    print(f"🎉 全部完成！")
    print(f"1. 原始 merged_output 檔案已保留不覆蓋。")
    print(f"2. 中借詞提取結果已存於: {NEW_OUTPUT_FOLDER}")

if __name__ == "__main__":
    main()
