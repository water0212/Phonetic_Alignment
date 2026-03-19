import pandas as pd
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
# 設定檔案路徑 (請修改為您實際的檔案路徑)
file_g = os.path.join(current_dir, 'LOOCV_Results改完字典查找G.xlsx')
file_d = os.path.join(current_dir, 'LOOCV_Results改完字典查找D.xlsx')

def compare_results(file_path_g, file_path_d):
    # 讀取 "詳細結果" sheet
    try:
        df_g = pd.read_excel(file_path_g, sheet_name='詳細結果')
        df_d = pd.read_excel(file_path_d, sheet_name='詳細結果')
    except Exception as e:
        print(f"讀取檔案失敗: {e}")
        return

    # 確保欄位名稱乾淨
    df_g.columns = df_g.columns.str.strip()
    df_d.columns = df_d.columns.str.strip()

    # 建立比較基準 (族語 + 中文詞彙)
    # 將兩個 dataframe 合併，suffix 分別標示 _G 和 _D
    merged = pd.merge(
        df_g[['族語', '中文詞彙', '是否完全正確', '測試過程與比對']],
        df_d[['族語', '中文詞彙', '是否完全正確', '測試過程與比對']],
        on=['族語', '中文詞彙'],
        suffixes=('_G優先', '_D優先'),
        how='inner'
    )

    # 找出結果不一致的列
    diff_rows = merged[merged['是否完全正確_G優先'] != merged['是否完全正確_D優先']].copy()

    if diff_rows.empty:
        print("兩個檔案的判斷結果完全一致！")
        return

    # 整理輸出格式
    output_data = []
    for index, row in diff_rows.iterrows():
        lang = row['族語']
        word = row['中文詞彙']
        res_g = row['是否完全正確_G優先']
        res_d = row['是否完全正確_D優先']
        
        # 判斷是變好還是變壞
        status = ""
        if res_g == "否" and res_d == "是":
            status = "🟢 變好 (D勝)"
        elif res_g == "是" and res_d == "否":
            status = "🔴 變差 (G勝)"
            
        output_data.append({
            "族語": lang,
            "中文詞彙": word,
            "變化狀態": status,
            "G優先結果": res_g,
            "D優先結果": res_d,
            "G優先_過程": row['測試過程與比對_G優先'],
            "D優先_過程": row['測試過程與比對_D優先']
        })

    df_output = pd.DataFrame(output_data)
    
    # 排序：先排語言，再排變化狀態
    df_output = df_output.sort_values(by=['族語', '變化狀態'], ascending=[True, False])

    # 輸出到 Excel
    output_file = '差異比較報告.xlsx'
    df_output.to_excel(output_file, index=False)
    print(f"✅ 比對完成！共發現 {len(df_output)} 處差異。")
    print(f"📄 詳細報告已儲存為: {output_file}")
    
    # 簡單印出摘要
    print("\n--- 差異摘要 ---")
    print(df_output[['族語', '中文詞彙', '變化狀態']].to_string(index=False))

if __name__ == "__main__":
    # 請確保檔案在同一目錄下，或修改上方路徑
    if os.path.exists(file_g) and os.path.exists(file_d):
        compare_results(file_g, file_d)
    else:
        print("❌ 找不到輸入檔案，請確認檔名與路徑。")
