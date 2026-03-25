import json
import os
import glob
from openpyxl import Workbook

cuurent_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(cuurent_dir, "zhconv_result.json")

def main():
    print("🚀 程式開始執行...")
    
    # 1. 讀取 JSON 檔案
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 2. 將資料轉換為 CSV 格式
    csv_lines = []
    for G_ID in data:
        line = ",".join([str(data[G_ID].get(key, "")) for key in ["lines", "total_num"]] + [str(x) for x in data[G_ID]["pair_num"]])  # 根據實際 JSON 結構調整鍵名
        csv_lines.append(line)
    
    # 3. 寫入 CSV 檔案
    output_file = os.path.join(cuurent_dir, "zhconv_result.csv")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(csv_lines))
    
    print(f"✅ 已成功將資料轉換為 CSV 並儲存至 {output_file}")
if __name__ == "__main__":    main()