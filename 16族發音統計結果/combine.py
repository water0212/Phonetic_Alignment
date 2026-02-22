import pandas as pd
import json
import os
import glob

def main():
    # --- 1. 設定路徑與搜尋檔案 ---
    # 取得目前腳本所在路徑
    base_path = os.path.dirname(os.path.abspath(__file__))
    
    # 搜尋所有 .json 結尾的檔案
    json_files = glob.glob(os.path.join(base_path, "*.json"))
    
    # 排序檔案，確保欄位是依照 01, 02, 03... 順序排列
    json_files.sort()

    if not json_files:
        print("錯誤：在資料夾中找不到任何 JSON 檔案。")
        return

    print(f"找到 {len(json_files)} 個 JSON 檔案，準備合併...")

    # --- 2. 資料彙整邏輯 ---
    # 使用字典來儲存結構：
    # data_map[(中文發音, 族語發音)] = { '檔名1': 次數, '檔名2': 次數 ... }
    data_map = {}
    
    # 儲存所有的檔名，用來當作 Excel 的欄位表頭
    all_filenames = []

    for file_path in json_files:
        # 取得檔名 (不含路徑與副檔名)，例如 "03_output_alignment_voted"
        filename = os.path.splitext(os.path.basename(file_path))[0]
        all_filenames.append(filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                
                # content 的結構是: { "b": {"p": 19}, "f": {"h": 5} ... }
                for chi_sound, ind_dict in content.items():
                    # 處理有些 key 是空字串的情況
                    if chi_sound == "": chi_sound = "(空)"
                    
                    for ind_sound, count in ind_dict.items():
                        if ind_sound == "": ind_sound = "(空)"
                        
                        # 建立唯一的 Key
                        key = (chi_sound, ind_sound)
                        
                        if key not in data_map:
                            data_map[key] = {}
                        
                        # 記錄該檔案的次數
                        data_map[key][filename] = count
                        
        except Exception as e:
            print(f"讀取檔案 {filename} 失敗: {e}")

    # --- 3. 轉換為 DataFrame ---
    rows = []
    for (chi, ind), file_counts in data_map.items():
        # 建立一列基本資料
        row_data = {
            "中文發音": chi,
            "族語發音": ind
        }
        # 填入各個檔案的計數 (如果該檔案沒有這個發音，稍後補 0)
        row_data.update(file_counts)
        rows.append(row_data)

    df = pd.DataFrame(rows)

    # 填補缺失值 (NaN -> 0)，並將數字轉為整數
    df = df.fillna(0)
    
    # 確保所有檔案欄位都是數字型態
    for fname in all_filenames:
        if fname in df.columns:
            df[fname] = df[fname].astype(int)

    # --- 4. 計算總計與排序 ---
    # 新增一個「總計」欄位，方便觀察
    df['總計'] = df[all_filenames].sum(axis=1)

    # 排序：先依中文發音 A-Z，再依總計次數由大到小
    df = df.sort_values(by=['中文發音', '總計'], ascending=[True, False])

    # 調整欄位順序：中文 -> 族語 -> 總計 -> 檔案1 -> 檔案2 ...
    cols = ['中文發音', '族語發音', '總計'] + all_filenames
    df = df[cols]

    # --- 5. 輸出 Excel ---
    OUTPUT_FILE = os.path.join(base_path, 'merged_pronunciation_stats.xlsx')
    
    try:
        # 使用 ExcelWriter 來設定格式 (選用)
        with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='合併統計')
            
        print("-" * 30)
        print("合併完成！")
        print(f"共處理了 {len(data_map)} 種發音組合。")
        print(f"檔案已儲存至: {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"儲存 Excel 失敗: {e}")

if __name__ == "__main__":
    main()
