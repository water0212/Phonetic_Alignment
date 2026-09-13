import os
import json
from collections import Counter

# 設定您的 merged 資料夾路徑
BASE_DIR = r"c:\Users\jimmy\OneDrive\桌面\台灣南島與新詞專題\新詞整合\新詞譯詞"
# 輸出的報告檔案名稱
REPORT_FILE = "semantic_report.txt"

def list_all_semantics():
    if not os.path.exists(BASE_DIR):
        print(f"❌ 找不到路徑: {BASE_DIR}")
        return

    # 統計計數器
    raw_types = Counter()
    total_files = 0

    print(f"🚀 正在掃描所有族語資料...\n")

    # 1. 遍歷資料夾
    for folder in os.listdir(BASE_DIR):
        folder_path = os.path.join(BASE_DIR, folder)
        
        if os.path.isdir(folder_path):
            json_path = os.path.join(folder_path, "merged_output.json")
            
            if os.path.exists(json_path):
                total_files += 1
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # 2. 抓取內容
                    for category, content in data.items():
                        if "new_word" in content:
                            for item in content["new_word"]:
                                # 取得內容並去除前後空白
                                semantic = item.get("ch_semantic", "").strip()
                                
                                if semantic:
                                    raw_types[semantic] += 1
                                else:
                                    raw_types["(空白/未填寫)"] += 1

                except Exception as e:
                    print(f"⚠️ 讀取 {folder} 失敗: {e}")

    # 3. 輸出結果
    output_lines = []
    output_lines.append(f"📊 統計報告 - 掃描了 {total_files} 個檔案")
    output_lines.append(f"總共有 {len(raw_types)} 種不同的寫法")
    output_lines.append("-" * 50)
    output_lines.append(f"{'次數':<8} | {'內容 (ch_semantic)'}")
    output_lines.append("-" * 50)

    # most_common() 不放數字就會列出全部
    for text, count in raw_types.most_common():
        line = f"{count:<8} | {text}"
        output_lines.append(line)
        print(line)  # 印在螢幕上

    # 4. 存檔 (怕螢幕洗版太快看不完)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    
    print("-" * 50)
    print(f"✅ 完整清單已列出，並同時儲存於檔案：{os.path.abspath(REPORT_FILE)}")

if __name__ == "__main__":
    list_all_semantics()
