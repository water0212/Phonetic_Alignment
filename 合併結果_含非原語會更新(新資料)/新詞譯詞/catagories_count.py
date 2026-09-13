import os
import json
import pandas as pd

# 設定您的 merged 資料夾路徑
BASE_DIR = r"c:\Users\jimmy\OneDrive\桌面\台灣南島與新詞專題\新詞整合\新詞譯詞"
# 輸出的 Excel 檔名
OUTPUT_FILE = "semantic_statistics.xlsx"

# 定義我們要統計的分類欄位
COLUMNS = ["中借", "日借", "閩借", "中借+日借", "未明說", "其他語", "空白"]

def classify_semantic(text):
    """
    根據使用者定義的規則進行分類
    """
    if not text:
        return "空白"
    
    # 1. 預處理：去除空白，統一全形＋號為半形+
    text = text.strip().replace("＋", "+")
    
    # 2. 優先判斷【中借+日借】(混合型)
    if "+" in text:
        has_zh = any(k in text for k in ["中", "華"])
        has_jp = "日" in text
        if has_zh and has_jp:
            return "中借+日借"

    # 3. 判斷【中借】
    if any(k in text for k in ["中譯", "中借", "華語直譯"]):
        return "中借"

    # 4. 判斷【日借】
    if any(k in text for k in ["日譯", "日語借詞", "日借"]):
        return "日借"

    # 5. 判斷【閩借】
    if any(k in text for k in ["閩譯", "閩借"]):
        return "閩借"

    # 6. 判斷【未明說】(音譯/直譯類)
    if any(k in text for k in ["音譯", "借詞", "音譯詞", "直譯"]):
        return "未明說"

    # 7. 判斷【其他語】
    return "其他語"

def export_to_excel():
    if not os.path.exists(BASE_DIR):
        print(f"❌ 找不到路徑: {BASE_DIR}")
        return

    print(f"🚀 正在掃描並計算數據...\n")

    # 用來儲存每一列的數據 (List of Dictionaries)
    all_data = []

    # 取得資料夾列表並排序
    folders = sorted(os.listdir(BASE_DIR))
    
    for folder in folders:
        folder_path = os.path.join(BASE_DIR, folder)
        
        if os.path.isdir(folder_path):
            json_path = os.path.join(folder_path, "merged_output.json")
            
            # 初始化該族的數據列
            row_data = {"族語名稱": folder}
            # 先把所有計數歸零
            for col in COLUMNS:
                row_data[col] = 0
            
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    for category, content in data.items():
                        if "new_word" in content:
                            for item in content["new_word"]:
                                raw_semantic = item.get("ch_semantic", "")
                                result_type = classify_semantic(raw_semantic)
                                
                                # 累加次數
                                row_data[result_type] += 1
                    
                    # 將這一族的數據加入總表
                    all_data.append(row_data)
                    print(f"   ✅ 已處理: {folder}")

                except Exception as e:
                    print(f"   ⚠️ 讀取 {folder} 失敗: {e}")

    # --- 轉成 DataFrame 並輸出 ---
    
    if not all_data:
        print("❌ 沒有讀取到任何資料，無法產生 Excel。")
        return

    # 建立 DataFrame
    df = pd.DataFrame(all_data)
    
    # 調整欄位順序 (把族語名稱放最前面，後面接我們定義的順序)
    final_columns = ["族語名稱"] + COLUMNS
    df = df[final_columns]

    # 計算【總計】列
    # sum(numeric_only=True) 會自動加總所有數字欄位
    sum_row = df.sum(numeric_only=True)
    sum_row["族語名稱"] = "總計"
    
    # 將總計列加到最後一行 (使用 pd.concat)
    df_sum = pd.DataFrame([sum_row])
    df = pd.concat([df, df_sum], ignore_index=True)

    # 存成 Excel
    try:
        df.to_excel(OUTPUT_FILE, index=False)
        print("-" * 40)
        print(f"🎉 成功！檔案已輸出至: {os.path.abspath(OUTPUT_FILE)}")
        print("您可以直接用 Excel 開啟查看。")
    except PermissionError:
        print(f"❌ 存檔失敗！請確認 {OUTPUT_FILE} 沒有被打開，關閉後再試一次。")

if __name__ == "__main__":
    export_to_excel()
